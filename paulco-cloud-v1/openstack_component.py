from flask import Flask, redirect, url_for, flash, render_template, request, jsonify, send_file
from flask_login import (
    LoginManager, UserMixin, current_user,
    login_required, login_user, logout_user
)
import openstack
import threading
import time
from datetime import datetime
from dateutil import parser
import pytz
from openstack import connection
#from models import User
from main import app, db # Ensure 'app' and 'db' are correctly imported from main.py
import yaml

# Establish OpenStack connection
conn = connection.Connection(cloud='admin')

def load_pricing():
    with open('pricing.yml', 'r') as f:
        return yaml.safe_load(f)

@app.context_processor
def inject_pricing():
    pricing = load_pricing()
    return dict(pricing=pricing)

# before_request function (for method override in forms)
@app.before_request
def before_request():
    if request.method == 'POST' and '_method' in request.form:
        request.method = request.form['_method'].upper()

# Instance Management Routes
@app.route('/instances', methods=['GET'])
@login_required
def list_instances():
    try:
        instances = conn.compute.servers(details=True)
        instance_list = []
        for instance in instances:
            addresses = instance.addresses
            instance_ips = []
            for network_name, network_addresses in addresses.items():
                for address_info in network_addresses:
                    instance_ips.append(address_info['addr'])

            instance_list.append({
                'name': instance.name,
                'status': instance.status,
                'id': instance.id,
                'flavor': instance.flavor['original_name'],
                'image': instance.image['name'],
                'ips': ', '.join(instance_ips) if instance_ips else 'N/A'
            })
        return render_template('cloud/list_instances.html', instances=instance_list )
    except Exception as e:
        flash(f'Error fetching instances: {str(e)}')
        return redirect('/')

@app.route('/instances/<instance_id>', methods=['DELETE'])
def delete_instance(instance_id):
    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            conn.compute.delete_server(instance)
            flash('Instance deleted successfully.')
        else:
            flash('Instance not found.')
    except Exception as e:
        flash(f'Error deleting instance: {str(e)}')
    return redirect('/instances')

@app.route('/instances/<instance_id>', methods=['GET'])
@login_required
def get_instance(instance_id):
    print(f"get_instance called for instance_id: {instance_id}")
    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            print(f"Instance found: {instance.name}, Status: {instance.status}")
            addresses = instance.addresses
            instance_ips = []
            for network_name, network_addresses in addresses.items():
                for address_info in network_addresses:
                    instance_ips.append(address_info['addr'])

            volumes = []
            volume_cost = 0
            if hasattr(instance, 'volume_attachments'):
                for volume_attachment in instance.volume_attachments:
                    volume = conn.volume.get_volume(volume_attachment['volume_id'])
                    if volume:
                        volumes.append({'name': volume.name, 'size': volume.size, 'id': volume.id})
                        # Calculate volume cost
                        creation_time_str = volume.created_at
                        creation_time = parser.parse(creation_time_str)
                        current_time = datetime.now(pytz.utc)
                        elapsed_time_hours = (current_time - creation_time).total_seconds() / 3600
                        volume_price_per_gb_hour = load_pricing()['volume_prices']['per_gb_per_hour']
                        volume_cost += elapsed_time_hours * volume.size * volume_price_per_gb_hour


            # Calculate instance runtime and flavor cost
            creation_time_str = instance.created_at
            creation_time = parser.parse(creation_time_str)
            current_time = datetime.now(pytz.utc)
            elapsed_time_hours = (current_time - creation_time).total_seconds() / 3600

            pricing_data = load_pricing()
            flavor_name = instance.flavor['original_name']
            flavor_price_per_hour = pricing_data['instance_flavor_prices'].get(flavor_name, 0)
            instance_flavor_cost = elapsed_time_hours * flavor_price_per_hour
            total_cost = instance_flavor_cost + volume_cost


            instance_info = {
                'name': instance.name,
                'status': instance.status,
                'id': instance.id,
                'flavor': instance.flavor['original_name'],
                'image': instance.image['name'],
                'created_at': instance.created_at,
                'updated_at': instance.updated_at,
                'ips': ', '.join(instance_ips) if instance_ips else 'N/A',
                'volumes': volumes,
                'security_groups': instance.security_groups,
                'runtime_hours': round(elapsed_time_hours, 2),
                'flavor_cost': round(instance_flavor_cost, 4),
                'volume_cost': round(volume_cost, 4),
                'total_cost': round(total_cost, 4)
            }
            print(f"Instance Info: {instance_info}")
            return render_template('cloud/instance_detail.html', instance=instance_info)
        else:
            print(f"Instance not found for instance_id: {instance_id}")
            flash('Instance not found.')
            return redirect('/instances')
    except Exception as e:
        print(f"Exception in get_instance: {e}")
        flash(f'Error fetching instance details: {str(e)}')
        return redirect('/instances')

@app.route('/create_instance', methods=['GET', 'POST'])
@login_required
def create_instance():
    if request.method == 'POST':
        name = request.form['name']
        image_id = request.form['image']
        flavor_id = request.form['flavor']
        network_id = request.form['network']
        keypair_name = request.form['keypair_name']
        volume_size = request.form.get('volume_size') # Get volume size from form

        block_device_mapping = []
        if volume_size:
            block_device_mapping.append({
                'volume_size': int(volume_size),
                'delete_on_termination': True,
                'device_name': 'vda' # Example device name
            })


        # Create key pair if name is provided
        if keypair_name:
            try:
                keypair = conn.compute.create_keypair(name=keypair_name)
                private_key = keypair.private_key
                with open(f"{keypair_name}.pem", "w") as key_file:
                    key_file.write(private_key)
                flash(f'New key pair {keypair_name} created successfully.')
            except Exception as e:
                flash(f'Error creating key pair: {str(e)}')

        # Create instance
        try:
            instance = conn.compute.create_server(
                name=name,
                image_id=image_id,
                flavor_id=flavor_id,
                networks=[{"uuid": network_id}],
                key_name=keypair_name,
                block_device_mapping=block_device_mapping if block_device_mapping else None # Attach volume if size is provided
            )
            instance = conn.compute.wait_for_server(instance)
            flash('Instance created successfully.')
            return redirect('/instances')
        except Exception as e:
            flash(f'Error creating instance: {str(e)}')

    images = conn.compute.images()
    flavors = conn.compute.flavors()
    networks = conn.network.networks()
    keypairs = conn.compute.keypairs()
    return render_template('cloud/create_instance.html', images=images, flavors=flavors, networks=networks, keypairs=keypairs)

@app.route('/instances/<instance_id>/start', methods=['POST'])
def start_instance(instance_id):
    try:
        instance = conn.compute.get_server(instance_id)
        if instance and instance.status != 'ACTIVE':
            conn.compute.start_server(instance)
            flash('Instance started successfully.')
        else:
            flash('Instance is already running or not found.')
    except Exception as e:
        flash(f'Error starting instance: {str(e)}')
    return redirect('/instances')

@app.route('/instances/<instance_id>/stop', methods=['POST'])
def stop_instance(instance_id):
    try:
        instance = conn.compute.get_server(instance_id)
        if instance and instance.status != 'SHUTOFF':
            conn.compute.stop_server(instance)
            flash('Instance stopped successfully.')
        else:
            flash('Instance is already stopped or not found.')
    except Exception as e:
        flash(f'Error stopping instance: {str(e)}')
    return redirect('/instances')

@app.route('/instances/<instance_id>/restart', methods=['POST'])
def restart_instance(instance_id):
    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            conn.compute.reboot_server(instance)
            flash('Instance restarted successfully.')
        else:
            flash('Instance not found.')
    except Exception as e:
        flash(f'Error restarting instance: {str(e)}')
    return redirect('/instances')

@app.route('/download_key/<key_name>', methods=['GET'])
def download_key(key_name):
    try:
        key_file_path = f"{key_name}.pem"
        return send_file(key_file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading key: {str(e)}')
        return redirect('/instances')

@app.route('/instances/<instance_id>/console', methods=['GET'])
@login_required
def get_instance_console(instance_id):
    print("get_instance_console function CALLED")
    print(f"Instance ID received in get_instance_console: {instance_id}")
    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            print(f"Instance found in get_instance_console: {instance.name}")
            try:
                console = conn.compute.get_console_url(instance, console_type='vnc') # Using get_console_url
                print(f"Console object: {console}")
                console_url = console.url
                print(f"Console URL: {console_url}")
                return render_template('cloud/instance_console.html', console_url=console_url, instance_name=instance.name)
            except Exception as console_e:
                print(f"Error generating console URL using get_console_url: {console_e}")
                flash(f'Error generating console URL: {str(console_e)}')
                return redirect('/instances')
        else:
            print(f"Instance NOT found in get_instance_console for ID: {instance_id}")
            flash('Instance not found.')
            return redirect('/instances')
    except Exception as e:
        print(f"Error in get_instance_console: {e}")
        flash(f'Error fetching instance details: {str(e)}')
        return redirect('/instances')

# Volume Management Routes
@app.route('/volumes', methods=['GET'])
@login_required
def list_volumes():
    try:
        volumes = conn.volume.volumes()
        return render_template('cloud/list_volumes.html', volumes=volumes)
    except Exception as e:
        flash(f'Error fetching volumes: {str(e)}')
        return redirect('/')

@app.route('/volumes/create', methods=['GET', 'POST'])
@login_required
def create_volume():
    if request.method == 'POST':
        name = request.form['name']
        size = int(request.form['size'])
        try:
            volume = conn.volume.create_volume(name=name, size=size)
            flash('Volume created successfully.')
            return redirect('/volumes')
        except Exception as e:
            flash(f'Error creating volume: {str(e)}')

    return render_template('cloud/create_volume.html')

@app.route('/volumes/<volume_id>/delete', methods=['POST'])
def delete_volume(volume_id):
    try:
        volume = conn.volume.get_volume(volume_id)
        if volume:
            conn.volume.delete_volume(volume)
            flash('Volume deleted successfully.')
        else:
            flash('Volume not found.')
    except Exception as e:
        flash(f'Error deleting volume: {str(e)}')
    return redirect('/volumes')

@app.route('/instances/<instance_id>/attach_volume', methods=['GET', 'POST'])
@login_required
def attach_volume_to_instance(instance_id):
    instance = conn.compute.get_server(instance_id)
    if not instance:
        flash('Instance not found.')
        return redirect('/instances')

    if request.method == 'POST':
        volume_id = request.form['volume_id']
        try:
            conn.compute.attach_volume(instance, volume=volume_id)
            flash(f'Volume attached to instance {instance.name} successfully.')
            return redirect(url_for('get_instance', instance_id=instance_id))
        except Exception as e:
            flash(f'Error attaching volume: {str(e)}')
            return redirect(url_for('get_instance', instance_id=instance_id))

    volumes = conn.volume.volumes()
    attached_volume_ids = [v['volume_id'] for v in instance.volume_attachments]
    available_volumes = [v for v in volumes if v.id not in attached_volume_ids] #Show only available volumes
    return render_template('cloud/attach_volume.html', instance=instance, volumes=available_volumes)


@app.route('/instances/<instance_id>/detach_volume/<volume_id>', methods=['POST'])
def detach_volume_from_instance(instance_id, volume_id):
    instance = conn.compute.get_server(instance_id)
    volume = conn.volume.get_volume(volume_id)

    if not instance or not volume:
        flash('Instance or Volume not found.')
        return redirect('/instances')

    try:
        conn.compute.detach_volume(instance, volume=volume)
        flash(f'Volume detached from instance {instance.name} successfully.')
    except Exception as e:
        flash(f'Error detaching volume: {str(e)}')
    return redirect(url_for('get_instance', instance_id=instance_id))


# Floating IP Management Routes
@app.route('/floating_ips', methods=['GET'])
@login_required
def list_floating_ips():
    try:
        floating_ips = conn.network.ips()
        return render_template('cloud/list_floating_ips.html', floating_ips=floating_ips)
    except Exception as e:
        flash(f'Error fetching floating IPs: {str(e)}')
        return redirect('/')

@app.route('/floating_ips/allocate', methods=['GET', 'POST'])
@login_required
def allocate_floating_ip():
    if request.method == 'POST':
        # Currently, pool is hardcoded as 'Public'. You might want to make it dynamic.
        pool_name = 'Public' # or request.form['pool_name'] if you want to make it selectable
        try:
            floating_ip = conn.network.create_ip(floating_ip_pool_name=pool_name)
            flash('Floating IP allocated successfully.')
            return redirect('/floating_ips')
        except Exception as e:
            flash(f'Error allocating floating IP: {str(e)}')

    return render_template('cloud/allocate_floating_ip.html')

@app.route('/floating_ips/<floating_ip_id>/release', methods=['POST'])
def release_floating_ip(floating_ip_id):
    try:
        floating_ip = conn.network.get_ip(floating_ip_id)
        if floating_ip:
            conn.network.delete_ip(floating_ip)
            flash('Floating IP released successfully.')
        else:
            flash('Floating IP not found.')
    except Exception as e:
        flash(f'Error releasing floating IP: {str(e)}')
    return redirect('/floating_ips')

@app.route('/instances/<instance_id>/associate_floating_ip', methods=['GET', 'POST'])
@login_required
def associate_floating_ip_to_instance(instance_id):
    instance = conn.compute.get_server(instance_id)
    if not instance:
        flash('Instance not found.')
        return redirect('/instances')

    if request.method == 'POST':
        floating_ip_id = request.form['floating_ip_id']
        try:
            conn.compute.add_floating_ip_to_server(
                instance, floating_ip=floating_ip_id
            )
            flash(f'Floating IP associated with instance {instance.name} successfully.')
            return redirect(url_for('get_instance', instance_id=instance_id))
        except Exception as e:
            flash(f'Error associating floating IP: {str(e)}')
            return redirect(url_for('get_instance', instance_id=instance_id))

    available_floating_ips = [
        ip for ip in conn.network.ips()
        if not ip.fixed_ip_address  # Show only unassociated IPs
    ]
    return render_template('cloud/associate_floating_ip.html', instance=instance, floating_ips=available_floating_ips)


@app.route('/instances/<instance_id>/disassociate_floating_ip/<floating_ip_id>', methods=['POST'])
def disassociate_floating_ip_from_instance(instance_id, floating_ip_id):
    instance = conn.compute.get_server(instance_id)
    floating_ip = conn.network.get_ip(floating_ip_id)

    if not instance or not floating_ip:
        flash('Instance or Floating IP not found.')
        return redirect('/instances')

    try:
        conn.compute.remove_floating_ip_from_server(instance, floating_ip=floating_ip)
        flash(f'Floating IP disassociated from instance {instance.name} successfully.')
    except Exception as e:
        flash(f'Error disassociating floating IP: {str(e)}')
    return redirect(url_for('get_instance', instance_id=instance_id))
