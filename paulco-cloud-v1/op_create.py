from flask import Flask, redirect, url_for, flash, render_template, request, jsonify, send_file
from main import app, db
from openstack import connection
from main import app, db, User, current_user  # Import the User model from your database
from flask_login import (
    LoginManager, UserMixin, current_user,
    login_required, login_user, logout_user
)
import secrets
import uuid

# Establish OpenStack connection
conn = connection.Connection(cloud='admin')


@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        # Get user input for project creation
        project_name = request.form.get("project_name")
        project_description = request.form.get("project_description")

        # Ensure project name is unique
        existing_project = conn.identity.find_project(name_or_id=project_name)
        if existing_project:
            flash(f"A project with the name '{project_name}' already exists.", "error")
            return redirect(url_for("create_project"))

        # Make project name unique by appending a random string
        project_name = f"{project_name}-{uuid.uuid4().hex[:6]}"

        # Get the current user's information
        user = User.query.filter_by(id=current_user.id).first()
        if not user or not user.username:
            flash("User not found or username is missing!", "error")
            return redirect(url_for("dashboard"))

        # Use a default username if username is missing
        username = user.username if user.username else f"user-{user.id}"

        try:
            # Step 1: Create a new project in OpenStack
            project = conn.identity.create_project(
                name=project_name,
                description=project_description,
                enabled=True
            )
            flash(f"Project '{project_name}' created successfully!", "success")

            # Step 2: Create a new user in OpenStack
            random_password = secrets.token_urlsafe(12)  # Generate a random password
            new_user = conn.identity.create_user(
                name=username,  # Use the username from the database or a default value
                password=random_password,
                email=user.email,
                default_project=project.id,  # Set the project as the primary project
                enabled=True
            )
            flash(f"User '{new_user.name}' created successfully in OpenStack!", "success")

            # Send the password to the user via email
            html = render_template('new_user_email.html', username=username, password=random_password)
            send_email(user.email, "Your New OpenStack Account", html)

            # Step 3: Assign the user to the project with a role
            role = conn.identity.find_role("member")  # Assuming "member" is the default role
            conn.identity.assign_project_role_to_user(
                project=project.id,
                user=new_user.id,
                role=role.id
            )
            flash(f"User '{new_user.name}' assigned to project '{project_name}' successfully!", "success")

            # Step 4: Create a private network for the project
            network = conn.network.create_network(
                name=f"{project_name}-private-network",
                project_id=project.id
            )
            subnet = conn.network.create_subnet(
                name=f"{project_name}-private-subnet",
                network_id=network.id,
                ip_version=4,
                cidr="192.168.1.0/24",  # Example CIDR block
                project_id=project.id
            )
            flash(f"Private network and subnet created for project '{project_name}'!", "success")

            # Redirect to the dashboard or project details page
            return redirect(url_for("dashboard"))

        except Exception as e:
            flash(f"Error creating project or user: {str(e)}", "error")
            print(f"Error creating project or user: {str(e)}")  # Log the error for debugging
            return redirect(url_for("create_project"))

    return render_template("cloud/create_project.html")

    if request.method == 'POST':
        # Get user input for project creation
        project_name = request.form.get("project_name")
        project_description = request.form.get("project_description")

        # Ensure project name is unique
        existing_project = conn.identity.find_project(name_or_id=project_name)
        if existing_project:
            flash(f"A project with the name '{project_name}' already exists.", "error")
            return redirect(url_for("create_project"))

        # Make project name unique by appending a random string
        project_name = f"{project_name}-{uuid.uuid4().hex[:6]}"

        # Get the current user's information
        user = User.query.filter_by(id=current_user.id).first()
        if not user:
            flash("User not found!", "error")
            return redirect(url_for("dashboard"))

        try:
            # Step 1: Create a new project in OpenStack
            project = conn.identity.create_project(
                name=project_name,
                description=project_description,
                enabled=True
            )
            flash(f"Project '{project_name}' created successfully!", "success")

            # Step 2: Create a new user in OpenStack
            random_password = secrets.token_urlsafe(12)  # Generate a random password
            new_user = conn.identity.create_user(
                name=user.username,
                password=random_password,
                email=user.email,
                default_project=project.id,  # Set the project as the primary project
                enabled=True
            )
            flash(f"User '{new_user.name}' created successfully in OpenStack!", "success")

            # Send the password to the user via email
            html = render_template('new_user_email.html', username=user.username, password=random_password)
            send_email(user.email, "Your New OpenStack Account", html)

            # Step 3: Assign the user to the project with a role
            role = conn.identity.find_role("member")  # Assuming "member" is the default role
            conn.identity.assign_project_role_to_user(
                project=project.id,
                user=new_user.id,
                role=role.id
            )
            flash(f"User '{new_user.name}' assigned to project '{project_name}' successfully!", "success")

            # Step 4: Create a private network for the project
            network = conn.network.create_network(
                name=f"{project_name}-private-network",
                project_id=project.id
            )
            subnet = conn.network.create_subnet(
                name=f"{project_name}-private-subnet",
                network_id=network.id,
                ip_version=4,
                cidr="192.168.1.0/24",  # Example CIDR block
                project_id=project.id
            )
            flash(f"Private network and subnet created for project '{project_name}'!", "success")

            # Redirect to the dashboard or project details page
            return redirect(url_for("dashboard"))

        except Exception as e:
            flash(f"Error creating project or user: {str(e)}", "error")
            print(f"Error creating project or user: {str(e)}")  # Log the error for debugging
            return redirect(url_for("create_project"))

    return render_template("cloud/create_project.html")