from flask import Flask, render_template, request, redirect, url_for, flash, session
from openstack import connection
from openstack.exceptions import ConflictException, NotFoundException

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Flask-এর জন্য সিক্রেট কী

# OpenStack সংযোগ তৈরি
def create_connection():
    return connection.Connection(cloud='openstack')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/create_project', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        project_name = request.form['project_name']
        username = request.form['username']
        password = request.form['password']

        try:
            conn = create_connection()

            # নতুন প্রজেক্ট তৈরি
            project = conn.identity.create_project(name=project_name)

            # নতুন ইউজার তৈরি
            user = conn.identity.create_user(name=username, password=password)

            # ইউজারের প্রাইমারি প্রজেক্ট সেট করুন
            conn.identity.update_user(user.id, default_project_id=project.id)

            # রোল খুঁজুন বা তৈরি করুন
            role_name = "member"
            role = conn.identity.find_role(role_name)
            if not role:
                role = conn.identity.create_role(name=role_name)

            # ইউজারকে প্রজেক্টে অ্যাড করুন
            conn.identity.assign_project_role_to_user(project.id, user.id, role.id)

            # সেশনে প্রজেক্ট এবং ইউজার তথ্য সংরক্ষণ
            session['project_id'] = project.id
            session['project_name'] = project.name
            session['username'] = username
            session['password'] = password

            flash(f"প্রজেক্ট '{project_name}' এবং ইউজার '{username}' সফলভাবে তৈরি হয়েছে!", 'success')
            return redirect(url_for('manage_project'))

        except ConflictException:
            flash(f"প্রজেক্ট বা ইউজার ইতিমধ্যেই বিদ্যমান!", 'error')
        except NotFoundException:
            flash(f"রোল বা অন্যান্য রিসোর্স খুঁজে পাওয়া যায়নি!", 'error')
        except Exception as e:
            flash(f"একটি ত্রুটি ঘটেছে: {str(e)}", 'error')

    return render_template('create_project.html')

@app.route('/manage_project', methods=['GET', 'POST'])
def manage_project():
    if 'project_id' not in session:
        flash("প্রথমে একটি প্রজেক্ট তৈরি করুন!", 'error')
        return redirect(url_for('home'))

    project_id = session['project_id']
    username = session['username']
    password = session['password']

    # প্রজেক্টের জন্য OpenStack সংযোগ তৈরি
    conn = connection.Connection(
        auth_url='http://192.168.0.50:5000/v3',
        project_id=project_id,
        username=username,
        password=password,
        user_domain_name='Default',
        project_domain_name='Default'
    )

    if request.method == 'POST':
        action = request.form.get('action')
        instance_id = request.form.get('instance_id')

        if action == 'create_instance':
            instance_name = request.form['instance_name']
            image_id = request.form['image_id']
            flavor_id = request.form['flavor_id']
            network_id = request.form['network_id']
            conn.create_server(
                name=instance_name,
                image_id=image_id,
                flavor_id=flavor_id,
                network_id=network_id
            )
            flash(f"ইনস্ট্যান্স '{instance_name}' সফলভাবে তৈরি হয়েছে!", 'success')

        elif action == 'delete_instance':
            conn.delete_server(instance_id)
            flash(f"ইনস্ট্যান্স ডিলিট করা হয়েছে!", 'success')

        elif action == 'start_instance':
            conn.start_server(instance_id)
            flash(f"ইনস্ট্যান্স স্টার্ট করা হয়েছে!", 'success')

        elif action == 'stop_instance':
            conn.stop_server(instance_id)
            flash(f"ইনস্ট্যান্স স্টপ করা হয়েছে!", 'success')

    # প্রজেক্টের আন্ডারে সকল ইনস্ট্যান্স লিস্ট ভিউ
    instances = list(conn.compute.servers())
    return render_template('manage_project.html', instances=instances)

if __name__ == '__main__':
    app.run(debug=True)