from flask import Blueprint, request, jsonify
from supabase_client import get_supabase
import os
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Initialize Supabase client
supabase = get_supabase()

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint that accepts user_id and password
    Authenticates via Supabase Auth and returns role-based redirect path
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        password = data.get('password')

        # Also support email-based login for backward compatibility
        email = data.get('email')

        if not password:
            return jsonify({'error': 'Password is required'}), 400

        # If user_id is provided, convert to email format
        if user_id and not email:
            # Check if it's a student user_id (STU format)
            if user_id.startswith('STU'):
                email = f"{user_id}@college.edu"
            else:
                # For admin or other users, use as-is if it's an email
                if '@' in user_id:
                    email = user_id
                else:
                    return jsonify({'error': 'Invalid user_id format'}), 400

        if not email:
            return jsonify({'error': 'user_id or email is required'}), 400

        # Authenticate with Supabase
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                return jsonify({'error': 'Invalid credentials'}), 401

            user = auth_response.user
            session = auth_response.session

            # Get role from user metadata
            role = user.user_metadata.get('role', 'student')

            # Determine redirect path based on role
            redirect_path = '/'
            if role == 'admin':
                redirect_path = '/admin/dashboard'
            elif role == 'student':
                redirect_path = '/student/dashboard'
            elif role == 'teacher':
                redirect_path = '/faculty/dashboard'

            # Get additional user data based on role
            user_data = None
            if role == 'student':
                # Get student data
                student_response = supabase.table('students').select('*').eq('auth_user_id', user.id).execute()
                if student_response.data:
                    user_data = student_response.data[0]

            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': role,
                    'user_metadata': user.user_metadata
                },
                'session': {
                    'access_token': session.access_token,
                    'refresh_token': session.refresh_token
                },
                'redirect_path': redirect_path,
                'user_data': user_data,
                'message': 'Login successful'
            }), 200

        except Exception as auth_error:
            error_message = str(auth_error)
            if 'Invalid login credentials' in error_message:
                return jsonify({'error': 'Invalid user_id or password'}), 401
            else:
                return jsonify({'error': f'Authentication failed: {error_message}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        role = data.get('role', 'student')
        phone = data.get('phone')
        
        if not email or not password or not full_name:
            return jsonify({'error': 'Email, password, and full name are required'}), 400
        
        # Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Create profile
            profile_data = {
                'id': response.user.id,
                'email': email,
                'full_name': full_name,
                'role': role,
                'phone': phone,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            profile_response = supabase.table('profiles').insert(profile_data).execute()
            
            return jsonify({
                'user': response.user.model_dump(),
                'profile': profile_response.data[0] if profile_response.data else None,
                'message': 'User registered successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create user'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        supabase.auth.sign_out()
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    try:
        # Get the authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401
        
        # Extract the token
        token = auth_header.replace('Bearer ', '')
        
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if user:
            # Get profile data
            profile_response = supabase.table('profiles').select('*').eq('id', user.user.id).execute()
            
            return jsonify({
                'user': user.user.model_dump(),
                'profile': profile_response.data[0] if profile_response.data else None
            }), 200
        else:
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    try:
        # Get the authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401
        
        # Extract the token
        token = auth_header.replace('Bearer ', '')
        
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        data['updated_at'] = datetime.now().isoformat()
        
        # Update profile
        response = supabase.table('profiles').update(data).eq('id', user.user.id).execute()
        
        return jsonify({
            'profile': response.data[0] if response.data else None,
            'message': 'Profile updated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        response = supabase.auth.reset_password_email(email)
        
        return jsonify({'message': 'Password reset email sent'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
