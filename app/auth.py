from flask import Blueprint, request, jsonify, redirect, url_for, render_template
import jwt
from .models import User
from . import db
from .forms import LoginForm, RegisterForm
from werkzeug.security import generate_password_hash, check_password_hash
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', form=form, error='User already exists')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password, form.password.data):
            token = jwt.encode({'user_id': user.id}, os.getenv('JWT_SECRET_KEY'), algorithm='HS256')
            response = redirect(url_for('main.index'))
            response.set_cookie('token', token)
            return response
        return render_template('login.html', form=form, error='Invalid credentials')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    response = redirect(url_for('main.index'))
    response.delete_cookie('token')
    return response