from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User
from flask_login import login_user, logout_user, login_required

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'email': data.get('email')})
    
    if user and check_password_hash(user['password'], data.get('password')):
        user_obj = User(user)
        login_user(user_obj)
        return jsonify({'message': 'Login successful'})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if db.users.find_one({'email': data.get('email')}):
        return jsonify({'error': 'Email already exists'}), 400
    
    user_data = {
        'email': data.get('email'),
        'password': generate_password_hash(data.get('password')),
        'username': data.get('username')
    }
    
    db.users.insert_one(user_data)
    return jsonify({'message': 'User created successfully'})

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}) 