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
from main import app, db
import yaml

# Establish OpenStack connection
conn = connection.Connection(cloud='paulco-demo')

def load_icons():
    with open('icons.yml', 'r') as f:
        return yaml.safe_load(f)

# Context Processor ফাংশন
@app.context_processor
def inject_icons():
    icons = load_icons()['icons']
    return dict(icons=icons) # টেমপ্লেটে 'icons' নামে ভেরিয়েবল পাঠানো হবে

'''
def stop_active_instances():
    while True:
        try:
            # Fetch all servers
            instances = conn.compute.servers()
            for instance in instances:
                if instance.status == 'ACTIVE':
                    uptime_metadata = instance.metadata.get('uptime') # মেটাডাটা থেকে আপটাইম পড়ুন
                    if uptime_metadata: # যদি আপটাইম মেটাডাটা থাকে
                        uptime_limit_minutes = int(uptime_metadata)
                    else:
                        uptime_limit_minutes = 10 # ডিফল্ট আপটাইম ১ মিনিট (যদি মেটাডাটা না থাকে)

                    # Check the time since the instance was created
                    creation_time_str = instance.created_at
                    creation_time = parser.parse(creation_time_str)
                    current_time = datetime.now(pytz.utc)
                    elapsed_time = (current_time - creation_time).total_seconds() / 60

                    # Stop the instance if it has been active for more than the defined uptime
                    if elapsed_time > uptime_limit_minutes:
                        conn.compute.stop_server(instance)
                        print(f'Stopped instance {instance.name} (ID: {instance.id}) after {uptime_limit_minutes} minutes.') # আইডি ও আপটাইম সহ লগ

        except Exception as e:
            print(f'Error checking instances: {str(e)}')

        time.sleep(60)  # Wait for 1 minute before checking again
        try:
            # Fetch all servers
            instances = conn.compute.servers()
            for instance in instances:
                if instance.status == 'ACTIVE':
                    # Check the time since the instance was created
                    creation_time_str = instance.created_at

                    # Parse the creation time string into a datetime object
                    creation_time = parser.parse(creation_time_str)  # This will be an aware datetime

                    # Get current time as an aware datetime in UTC
                    current_time = datetime.now(pytz.utc)

                    # Calculate elapsed time in minutes
                    elapsed_time = (current_time - creation_time).total_seconds() / 60  # Convert to minutes

                    # Stop the instance if it has been active for more than 1 minute
                    if elapsed_time > 10:
                        conn.compute.stop_server(instance)
                        print(f'Stopped instance {instance.name} after exceeding time limit.')

        except Exception as e:
            print(f'Error checking instances: {str(e)}')

        time.sleep(60)  # Wait for 1 minute before checking again

# Start the background thread
threading.Thread(target=stop_active_instances, daemon=True).start()

'''

@app.before_request
def before_request():
    if request.method == 'POST' and '_method' in request.form:
        request.method = request.form['_method'].upper()

@app.route('/instances', methods=['GET'])
@login_required
def list_instances():
    try:
        # Fetching instances from OpenStack with more details
        instances = conn.compute.servers(details=True) # details=True যোগ করা হয়েছে
        instance_list = []
        for instance in instances:
            # IP address বের করার চেষ্টা (নেটওয়ার্কিং কনফিগারেশনের উপর ভিত্তি করে পরিবর্তন হতে পারে)
            addresses = instance.addresses
            instance_ips = []
            for network_name, network_addresses in addresses.items():
                for address_info in network_addresses:
                    instance_ips.append(address_info['addr'])


            instance_list.append({
                'name': instance.name,
                'status': instance.status,
                'id': instance.id,
                'flavor': instance.flavor['original_name'], # ফ্লেভার যোগ করা হলো
                'image': instance.image['name'], # ইমেজ যোগ করা হলো
                'ips': ', '.join(instance_ips) if instance_ips else 'N/A' # IP ঠিকানা যোগ করা হলো
            })
        return render_template('cloud/list_instances.html', instances=instance_list)
    except Exception as e:
        flash(f'Error fetching instances: {str(e)}')  # Provide user feedback
        return redirect('/')  # Redirect if there's an error

@app.route('/instances/<instance_id>', methods=['DELETE'])
def delete_instance(instance_id):
    try:
        instance = conn.compute.get_server(instance_id)  # Get the specific instance
        if instance:
            conn.compute.delete_server(instance)  # Delete the instance
            flash('Instance deleted successfully.')
        else:
            flash('Instance not found.')
    except Exception as e:
        flash(f'Error deleting instance: {str(e)}')
    return redirect('/instances')


@app.route('/instances/<instance_id>', methods=['GET'])
@login_required # ডিটেইল পেজ দেখার জন্য লগইন আবশ্যক
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
            # ** volume_attachments আছে কিনা পরীক্ষা করুন **
            if hasattr(instance, 'volume_attachments'):
                for volume_attachment in instance.volume_attachments:
                    volume = conn.volume.get_volume(volume_attachment['volume_id'])
                    if volume:
                        volumes.append({'name': volume.name, 'size': volume.size, 'id': volume.id})
            else:
                print("Warning: volume_attachments attribute not found in Server object.") # লগিং যোগ করা হলো

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
                'security_groups': instance.security_groups
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
    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            addresses = instance.addresses
            instance_ips = []
            for network_name, network_addresses in addresses.items():
                for address_info in network_addresses:
                    instance_ips.append(address_info['addr'])

            # ভলিউম তথ্য সংগ্রহ
            volumes = []
            for volume_attachment in instance.volume_attachments:
                volume = conn.volume.get_volume(volume_attachment['volume_id'])
                if volume:
                    volumes.append({'name': volume.name, 'size': volume.size, 'id': volume.id})


            instance_info = {
                'name': instance.name,
                'status': instance.status,
                'id': instance.id,
                'flavor': instance.flavor['original_name'],
                'image': instance.image['name'],
                'created_at': instance.created_at,
                'updated_at': instance.updated_at,
                'ips': ', '.join(instance_ips) if instance_ips else 'N/A',
                'volumes': volumes, # ভলিউম তথ্য যোগ করা হলো
                'security_groups': instance.security_groups # সিকিউরিটি গ্রুপ তথ্য
                # ভবিষ্যতে আরও তথ্য যোগ করা যেতে পারে
            }
            return render_template('cloud/instance_detail.html', instance=instance_info) # নতুন টেমপ্লেট ব্যবহার করা হবে
        else:
            flash('Instance not found.')
            return redirect('/instances')
    except Exception as e:
        print(f"Exception in get_instance: {e}") # লাইন যোগ করুন
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

        # Create a new key pair if a name is provided
        if keypair_name:
            try:
                keypair = conn.compute.create_keypair(name=keypair_name)
                # Save the private key to a file or database if needed
                private_key = keypair.private_key
                with open(f"{keypair_name}.pem", "w") as key_file:
                    key_file.write(private_key)
                flash(f'New key pair {keypair_name} created successfully.')
            except Exception as e:
                flash(f'Error creating key pair: {str(e)}')

        # Create the instance
        try:
            instance = conn.compute.create_server(
                name=name,
                image_id=image_id,
                flavor_id=flavor_id,
                networks=[{"uuid": network_id}],
                key_name=keypair_name  # Associate the new key pair with the instance
            )
            instance = conn.compute.wait_for_server(instance)
            flash('Instance created successfully.')
            return redirect('/instances')
        except Exception as e:
            flash(f'Error creating instance: {str(e)}')

    images = conn.compute.images()
    flavors = conn.compute.flavors()
    networks = conn.network.networks()
    keypairs = conn.compute.keypairs() # কিপেয়ার লিস্ট যুক্ত করা হলো
    return render_template('cloud/create_instance.html', images=images, flavors=flavors, networks=networks, keypairs=keypairs) #টেমপ্লেটে কিপেয়ার লিস্ট পাঠানো হলো

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
            conn.compute.reboot_server(instance)  # You can also use soft reboot if needed
            flash('Instance restarted successfully.')
        else:
            flash('Instance not found.')
    except Exception as e:
        flash(f'Error restarting instance: {str(e)}')
    return redirect('/instances')

@app.route('/download_key/<key_name>', methods=['GET'])
def download_key(key_name):
    try:
        # Assuming keys are stored in a specific directory
        key_file_path = f"{key_name}.pem"
        return send_file(key_file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading key: {str(e)}')
        return redirect('/instances')

# ** নতুন রাউট এবং ফাংশন - ইনস্ট্যান্স কনসোল **
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
                # `get_vnc_console` এর পরিবর্তে `get_console_url` ব্যবহার করা হচ্ছে
                console = conn.compute.get_console_url(instance, console_type='vnc') # console_type='vnc' অথবা 'VNC' ব্যবহার করে দেখুন
                print(f"Console object: {console}")
                console_url = console.url
                print(f"Console URL: {console_url}")
                return render_template('cloud/instance_console.html', console_url=console_url, instance_name=instance.name)
            except Exception as console_e:
                print(f"Error generating console URL using get_console_url: {console_e}") # এরর মেসেজ পরিবর্তন করা হলো
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
    print("get_instance_console function CALLED") # ফাংশন কলিং লগ
    print(f"Instance ID received in get_instance_console: {instance_id}") # ইনস্ট্যান্স আইডি লগ

    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            print(f"Instance found in get_instance_console: {instance.name}")
            try: # কনসোল URL জেনারেশনের জন্য try-except
                console = conn.compute.get_vnc_console(instance, console_type='VNC')
                print(f"Console object: {console}") # কনসোল অবজেক্ট প্রিন্ট করুন
                console_url = console.url
                print(f"Console URL: {console_url}") # কনসোল URL প্রিন্ট করুন
                return render_template('cloud/instance_console.html', console_url=console_url, instance_name=instance.name)
            except Exception as console_e: # কনসোল URL এরর হ্যান্ডলিং
                print(f"Error generating console URL: {console_e}") # কনসোল URL এরর লগ করুন
                flash(f'Error generating console URL: {str(console_e)}')
                return redirect('/instances') # এরর হলে রিডাইরেক্ট করুন
        else:
            print(f"Instance NOT found in get_instance_console for ID: {instance_id}")
            flash('Instance not found.')
            return redirect('/instances')
    except Exception as e:
        print(f"Error in get_instance_console: {e}")
        flash(f'Error fetching console URL: {str(e)}')
        return redirect('/instances')
    try:
        instance = conn.compute.get_server(instance_id)
        if instance:
            # ** এখানে কনসোল URL পাওয়ার জন্য লজিক যোগ করতে হবে **
            # ওপেনস্ট্যাক API থেকে কনসোল URL জেনারেট করার বিভিন্ন পদ্ধতি আছে, যেমন 'get_console_url'
            # অথবা 'get_vnc_console' ইত্যাদি। আপনার ওপেনস্ট্যাক এনভায়রনমেন্টে যেটা সাপোর্ট করে সেটা ব্যবহার করতে হবে।
            # নিচের কোডটি একটি উদাহরণ, যা সম্ভবত VNC কনসোল URL জেনারেট করবে।
            console = conn.compute.get_vnc_console(instance, console_type='VNC') # VNC কনসোল টাইপ ব্যবহার করা হলো
            console_url = console.url

            return render_template('cloud/instance_console.html', console_url=console_url, instance_name=instance.name) # নতুন টেমপ্লেট 'instance_console.html' ব্যবহার করা হবে
        else:
            flash('Instance not found.')
            return redirect('/instances')
    except Exception as e:
        flash(f'Error fetching console URL: {str(e)}')
        return redirect('/instances')