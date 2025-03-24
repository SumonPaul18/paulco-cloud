from flask import Flask, redirect, url_for, flash, render_template, request
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
from flask import send_file
from flask import Flask, jsonify, request, render_template, flash, redirect
from openstack import connection
from main import app, db
#from models import User

# Establish OpenStack connection
conn = connection.Connection(cloud='paulco-demo')


def stop_active_instances():
    while True:
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
                    if elapsed_time > 1:
                        conn.compute.stop_server(instance)
                        print(f'Stopped instance {instance.name} after exceeding time limit.')

        except Exception as e:
            print(f'Error checking instances: {str(e)}')

        time.sleep(60)  # Wait for 1 minute before checking again

# Start the background thread
threading.Thread(target=stop_active_instances, daemon=True).start()


@app.before_request
def before_request():
    if request.method == 'POST' and '_method' in request.form:
        request.method = request.form['_method'].upper()

@app.route('/instances', methods=['GET'])
@login_required
def list_instances():
    try:
        # Fetching instances from OpenStack
        instances = conn.compute.servers()
        instance_list = [{'name': instance.name, 'status': instance.status, 'id': instance.id} for instance in instances]
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
def get_instance(instance_id):
    instance = conn.compute.get_server(instance_id)
    if instance:
        instance_info = {'name': instance.name, 'status': instance.status, 'id': instance.id}
        return jsonify(instance_info)
    else:
        return jsonify({'error': 'Instance not found'}), 404

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
    return render_template('cloud/create_instance.html', images=images, flavors=flavors, networks=networks)

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

