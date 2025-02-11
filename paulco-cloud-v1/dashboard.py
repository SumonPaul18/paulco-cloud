from flask import Flask, redirect, url_for, flash, render_template, request
from flask_login import (
    LoginManager, UserMixin, current_user,
    login_required, login_user, logout_user
)
from main import app, db
#from models import User

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('sidebar.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/task')
@login_required
def task():
    return render_template('task.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Add registration logic here
        pass
    return render_template('register.html')

@app.route('/notification')
@login_required
def notification():
    return render_template('notification.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/cloud')
@login_required
def cloud():
    return render_template('cloud.html')

@app.route('/create_project')
@login_required
def create_project():
    return render_template('create_project2.html')

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/solutions')
def solutions():
    return render_template('solutions.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/send_contact', methods=['POST'])
def send_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # Here you would typically send an email or save the message to a database
    # For demonstration, we'll just flash a message and redirect back to contact page
    flash('Your message has been sent successfully!', 'success')
    
    return redirect(url_for('contact'))

