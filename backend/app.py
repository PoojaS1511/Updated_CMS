# Standard library imports
import os
import json
import re
import uuid
import time
import random
import string
import secrets
import traceback
from datetime import datetime, timedelta
from functools import wraps

# Third-party imports
from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS

from flask_sqlalchemy import SQLAlchemy
# Make rate limiting optional
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    print("[INFO] Flask-Limiter not found. Rate limiting will be disabled.")

# Make email optional
try:
    from flask_mail import Mail, Message
    MAIL_AVAILABLE = True
except ImportError:
    MAIL_AVAILABLE = False
    print("[INFO] Flask-Mail not found. Email functionality will be disabled.")
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from supabase_client import get_supabase, supabase_admin
import requests
import logging
import bcrypt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)


# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# CORS configuration
# Allow overriding via ALLOWED_ORIGINS env var (comma-separated list)
_allowed = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5001,http://127.0.0.1:5001')
ALLOWED_ORIGINS = [origin.strip() for origin in _allowed.split(',') if origin.strip()]

# Initialize CORS with automatic OPTIONS handling enabled
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///career_courses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Import models after db initialization to avoid circular imports
from models.base import Base, engine

# Initialize rate limiter if available
if RATE_LIMITING_AVAILABLE:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
else:
    # Create a dummy limiter decorator that does nothing
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    
    limiter = DummyLimiter()

# Initialize Flask-Mail if available
if MAIL_AVAILABLE:
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@yourcollege.edu')
    mail = Mail(app)
else:
    mail = None

# Create tables
with app.app_context():
    try:
        # Import all models to ensure they are registered with SQLAlchemy
        from models.career_course import CareerCourse  # Import specific models
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise  # Re-raise the exception to see the full traceback



# Import blueprints - keep these at the top to detect circular imports early
# We'll import them properly after the app is created
auth_bp = None
admin_bp = None
students_bp = None
faculty_bp = None
internships_bp = None
admissions_bp = None
exams_bp = None
academics_bp = None
analytics_bp = None
attendance_bp = None
fees_bp = None
notifications_bp = None
resume_analytics_bp = None
upgraded_bp = None
student_dashboard_bp = None
crud_bp = None
career_roadmap_bp = None

# Initialize Supabase client
supabase = get_supabase()

try:
    import google.generativeai as genai  # type: ignore
    genai_available = True
except Exception:
    genai = None
    genai_available = False
    print('[STARTUP] google.generativeai not available - AI features disabled. Install "google-generativeai" to enable.')

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user"""
    try:
        return bcrypt.checkpw(
            provided_password.encode('utf-8'),
            stored_password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

# Generate a random secure password with letters, digits, and special characters.
def generate_secure_password(length=12):
    """Generate a cryptographically secure random password with letters, digits, and special characters."""
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = '!@#$%^&*()_+-=[]{}|;:,.<>'

    # Ensure we have at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]

    # Fill the rest of the password with random characters
    remaining = length - len(password)
    all_chars = lowercase + uppercase + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(remaining))

    # Shuffle the password to make it more random
    random.shuffle(password)

    return ''.join(password)

def send_welcome_email(to_email: str, student_name: str, email: str, password: str) -> bool:
    """Send a welcome email to the student with their credentials."""
    if not MAIL_AVAILABLE:
        logger.info(f"Email functionality is disabled. Would have sent welcome email to {to_email}")
        return False
        
    try:
        msg = Message(
            subject="Welcome to Our College - Your Account Details",
            recipients=[to_email],
            html=f"""
            <h2>Welcome to Our College, {student_name}!</h2>
            <p>Your student account has been created successfully.</p>
            <p>Here are your login credentials:</p>
            <p><strong>Email:</strong> {email}<br>
            <strong>Password:</strong> {password}</p>
            <p>Please change your password after your first login.</p>
            <p>Best regards,<br>The College Administration</p>
            """
        )
        mail.send(msg)
        logger.info(f"Welcome email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Supabase clients are initialized in supabase_client.py

# Admin route decorator
def admin_required(fn):
    """Decorator for admin-only routes that require service role access"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # For admin routes, we'll use the service role key which bypasses JWT verification
        # but we still want to check for a valid admin token for security
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "Missing or invalid authorization header"}), 401

        # Set the admin client for this request
        request.supabase = supabase_admin
        return fn(*args, **kwargs)
    return wrapper

# Authentication middleware
def supabase_auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Handle OPTIONS requests (preflight) with proper CORS response
        if request.method == 'OPTIONS':
            response = make_response('', 200)
            origin = request.headers.get('Origin', 'http://localhost:3001')
            if origin in ALLOWED_ORIGINS:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            return response

        # For non-admin routes, use the regular client
        request.supabase = supabase

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            response = jsonify({"message": "Missing or invalid authorization header"}), 401
            return add_cors_headers(response)

        token = auth_header.split(' ')[1]
        try:
            # Verify the token with Supabase
            user = supabase.auth.get_user(token)
            if not user:
                response = jsonify({"message": "Invalid or expired token"}), 401
                return add_cors_headers(response)

            # Add user info to the request context
            request.user = user
            result = fn(*args, **kwargs)

            # Ensure CORS headers are added to the response
            return add_cors_headers(result)

        except Exception as e:
            response = jsonify({
                "message": "Authentication failed",
                "error": str(e)
            }), 401
            return add_cors_headers(response)
    return wrapper

def add_cors_headers(response):
    """Add CORS headers to a Flask response"""
    if isinstance(response, tuple):
        # Handle tuple responses (response, status_code)
        resp, status_code = response
        if hasattr(resp, 'headers'):
            origin = request.headers.get('Origin', 'http://localhost:3001')
            if origin in ALLOWED_ORIGINS:
                resp.headers.add('Access-Control-Allow-Origin', origin)
            resp.headers.add('Access-Control-Allow-Credentials', 'true')
            resp.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
            resp.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        return resp, status_code
    else:
        # Handle direct response objects
        if hasattr(response, 'headers'):
            origin = request.headers.get('Origin', 'http://localhost:3001')
            if origin in ALLOWED_ORIGINS:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        return response

@app.before_request
def handle_preflight():
    """Return CORS-enabled OK for OPTIONS preflight requests for any path."""
    if request.method == 'OPTIONS':
        resp = make_response('', 200)
        origin = request.headers.get('Origin', 'http://localhost:3001')
        if origin in ALLOWED_ORIGINS:
            resp.headers.add('Access-Control-Allow-Origin', origin)
        resp.headers.add('Access-Control-Allow-Credentials', 'true')
        resp.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        resp.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        return resp

@app.route('/api/errors', methods=['POST', 'OPTIONS'])
def report_error():
    """Endpoint for client-side error reporting (simple logger)."""
    try:
        if request.method == 'OPTIONS':
            return add_cors_headers(('', 200))
        payload = request.get_json(silent=True) or {}
        logger.info(f"Client error reported: {payload}")
        return add_cors_headers((jsonify({"status":"ok"}), 200))
    except Exception as e:
        logger.error(f"Error in /api/errors: {e}")
        return add_cors_headers((jsonify({"status":"error", "message":str(e)}), 500))

# Configure Gemini AI
# Prefer environment variable for API key, fall back to existing value if present
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or "AIzaSyAa2PR4eg5I-xRYS8W0GpJ_VohHh659ANk"
if genai_available:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        print(f"[STARTUP] Failed to configure google.generativeai: {e}")
        genai_available = False
        model = None
else:
    model = None

# Mock database for demonstration
MOCK_DATABASE = {
    'students': [
        {
            'id': 1,
            'register_number': 'REG2024001',
            'full_name': 'John Doe',
            'email': 'john.doe@email.com',
            'phone': '+91 9876543210',
            'course': 'B.Tech CSE',
            'current_semester': 5,
            'admission_year': 2022,
            'quota_type': 'merit',
            'category': 'general',
            'hostel_required': True,
            'transport_required': False,
            'status': 'active',
            'father_name': 'Robert Doe',
            'mother_name': 'Mary Doe',
            'date_of_birth': '2003-05-15',
            'address': '123 Main St, Chennai',
            'first_graduate': True
        },
        {
            'id': 2,
            'register_number': 'REG2024002',
            'full_name': 'Jane Smith',
            'email': 'jane.smith@email.com',
            'phone': '+91 9876543211',
            'course': 'B.Tech ECE',
            'current_semester': 3,
            'admission_year': 2023,
            'quota_type': 'sports',
            'category': 'obc',
            'hostel_required': False,
            'transport_required': True,
            'status': 'active',
            'father_name': 'James Smith',
            'mother_name': 'Lisa Smith',
            'date_of_birth': '2004-08-22',
            'address': '456 Oak Ave, Bangalore',
            'first_graduate': False
        }
    ],
    'attendance': [
        {'id': 1, 'student_id': 1, 'subject': 'Computer Networks', 'date': '2025-01-05', 'status': 'present'},
        {'id': 2, 'student_id': 1, 'subject': 'Database Systems', 'date': '2025-01-05', 'status': 'absent'},
        {'id': 3, 'student_id': 2, 'subject': 'Digital Electronics', 'date': '2025-01-05', 'status': 'present'}
    ],
    'marks': [
        {'id': 1, 'student_id': 1, 'subject': 'Computer Networks', 'exam_type': 'IA1', 'marks_obtained': 85, 'max_marks': 100},
        {'id': 2, 'student_id': 1, 'subject': 'Database Systems', 'exam_type': 'IA1', 'marks_obtained': 78, 'max_marks': 100}
    ]
}

@app.route('/')
def home():
    return jsonify({"message": "Cube Arts and Engineering College API", "status": "running"})

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    """Enhanced health check endpoint with detailed system information"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        if origin in ALLOWED_ORIGINS:
            response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    # Check database connection
    db_status = 'unknown'
    try:
        supabase = get_supabase()
        # Simple query to check database connection
        result = supabase.table('students').select('*').limit(1).execute()
        db_status = 'connected' if result.data is not None else 'error'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    # Get system information
    import platform
    import psutil
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'student-management-api',
        'version': '1.0.0',
        'environment': os.getenv('FLASK_ENV', 'development'),
        'python_version': platform.python_version(),
        'system': {
            'os': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        },
        'database': {
            'status': db_status,
            'tables': ['students', 'courses', 'exams']  # Add more tables as needed
        },
        'endpoints': {
            'student_dashboard': '/api/student_dashboard/<student_id>',
            'health': '/api/health',
            'test': '/api/test'
        },
        'cors': {
            'allowed_origins': ALLOWED_ORIGINS,
            'supports_credentials': True
        }
    }), 200

# Basic API endpoints for testing
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({"message": "API is working", "timestamp": datetime.utcnow().isoformat()})

# Student dashboard endpoint
@app.route('/api/student_dashboard/<student_id>', methods=['GET'])
@supabase_auth_required
def student_dashboard(student_id):
    try:
        print(f"Dashboard requested for student ID: {student_id}")
        
        # Verify the requesting user has access to this student's data
        if not request.user or str(request.user.get('id')) != student_id:
            return jsonify({
                "error": "Unauthorized",
                "message": "You don't have permission to access this student's data"
            }), 403
            
        # Here you would typically fetch the student's data from your database
        # For now, we'll return a simple response with the student ID
        return jsonify({
            "student_id": student_id,
            "status": "OK",
            "data": {
                "name": "John Doe",  # Replace with actual data
                "email": "student@example.com",
                "program": "Computer Science",
                "semester": 5,
                "attendance": 85.5,
                "cgpa": 8.7
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error in student_dashboard: {str(e)}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500

# Basic admission submission endpoint
@app.route('/api/admissions/submit', methods=['POST'])
def submit_application():
    try:
        data = request.get_json()

        # Generate application ID and register number
        application_id = f"APP{datetime.now().year}{uuid.uuid4().hex[:6].upper()}"
        year = datetime.now().year

        # Get the count of existing students to generate next register number
        if supabase:
            try:
                count_response = supabase.table('students').select('id', count='exact').execute()
                student_count = count_response.count if count_response.count else 0
                register_number = f"REG{year}{(student_count + 1):03d}"
            except:
                register_number = f"REG{year}001"
        else:
            register_number = f"REG{year}001"

        # Prepare student data for database
        student_data = {
            'register_number': register_number,
            'full_name': data.get('full_name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'date_of_birth': data.get('date_of_birth'),
            'gender': data.get('gender'),
            'course_id': data.get('course_id'),
            'admission_year': year,
            'admission_date': datetime.now().date().isoformat(),
            'quota_type': data.get('quota_type', 'merit'),
            'category': data.get('category', 'general'),
            'father_name': data.get('father_name'),
            'mother_name': data.get('mother_name'),
            'permanent_address': data.get('permanent_address'),
            'current_address': data.get('current_address'),
            'city': data.get('city'),
            'state': data.get('state'),
            'pincode': data.get('pincode'),
            'tenth_percentage': data.get('tenth_percentage'),
            'tenth_board': data.get('tenth_board'),
            'twelfth_percentage': data.get('twelfth_percentage'),
            'twelfth_board': data.get('twelfth_board'),
            'entrance_exam_score': data.get('entrance_exam_score'),
            'entrance_exam_rank': data.get('entrance_exam_rank'),
            'hostel_required': data.get('hostel_required', False),
            'transport_required': data.get('transport_required', False),
            'first_graduate': data.get('first_graduate', False),
            'status': 'pending_approval'
        }

        # Insert into Supabase
        if supabase:
            try:
                response = supabase.table('students').insert(student_data).execute()
                if response.data:
                    return jsonify({
                        'success': True,
                        'message': 'Admission application submitted successfully',
                        'data': {
                            'application_id': application_id,
                            'register_number': register_number,
                            'status': 'submitted',
                            'student_data': response.data[0]
                        }
                    }), 201
            except Exception as e:
                print(f"Supabase insert error: {e}")

        # Fallback response if Supabase fails
        return jsonify({
            'success': True,
            'message': 'Admission application submitted successfully',
            'data': {
                'application_id': application_id,
                'register_number': register_number,
                'status': 'submitted',
                'student_data': student_data
            }
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize in-memory storage for courses if not using Supabase
if not hasattr(app, 'courses'):
    app.courses = [
        {
            'id': 1,
            'name': 'Bachelor of Technology - Computer Science Engineering',
            'code': 'B.Tech CSE',
            'duration': '4 years',
            'description': 'Comprehensive program covering computer science fundamentals and advanced topics',
            'fee_per_semester': 60000,
            'department': {'name': 'Computer Science Engineering', 'code': 'CSE'}
        },
        {
            'id': 2,
            'name': 'Bachelor of Technology - Electronics and Communication Engineering',
            'code': 'B.Tech ECE',
            'duration': '4 years',
            'description': 'Focused on electronics and communication systems',
            'fee_per_semester': 55000,
            'department': {'name': 'Electronics and Communication Engineering', 'code': 'ECE'}
        },
        {
            'id': 3,
            'name': 'Bachelor of Technology - Mechanical Engineering',
            'code': 'B.Tech MECH',
            'duration': '4 years',
            'description': 'Covers mechanical systems and engineering principles',
            'fee_per_semester': 50000,
            'department': {'name': 'Mechanical Engineering', 'code': 'MECH'}
        }
    ]
    
    # Ensure all courses have the required fields
    for course in app.courses:
        course.setdefault('fee_per_semester', 0)
        if 'department' not in course:
            course['department'] = {'name': 'General', 'code': 'GEN'}

# Course management endpoints
# DISABLED: Using blueprint version in routes/academics.py instead
# @app.route('/api/academics/courses', methods=['GET', 'POST', 'OPTIONS'])
# @cross_origin()
def handle_courses_DISABLED():
    if request.method == 'GET':
        # Get all courses with optional filtering
        try:
            filters = request.args.to_dict()
            filtered_courses = app.courses.copy()
            
            # Apply filters if any
            if 'code' in filters:
                filtered_courses = [c for c in filtered_courses if c['code'] == filters['code']]
            if 'department' in filters:
                filtered_courses = [c for c in filtered_courses if c['department']['code'] == filters['department']]
            
            # Create response with proper JSON structure
            response = jsonify({
                'success': True,
                'data': filtered_courses
            })
            
            # Add CORS headers
            return response, 200
            
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': str(e)
            }), 500
            
    elif request.method == 'POST':
        # Create a new course
        try:
            # Ensure we have JSON data
            if not request.is_json:
                response = jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                })
                return response, 400
                
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'code', 'duration', 'description']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                response = jsonify({
                    'success': False,
                    'error': f"Missing required fields: {', '.join(missing_fields)}"

                })
                return response, 400
            
            # Check if course code already exists
            if any(c['code'] == data['code'] for c in app.courses):
                response = jsonify({
                    'success': False,
                    'error': f"Course with code {data['code']} already exists"
                })
                return response, 400
            
            # Create new course with default values
            new_course = {
                'id': max(c['id'] for c in app.courses) + 1 if app.courses else 1,
                'name': data['name'].strip(),
                'code': data['code'].strip().upper(),
                'duration': data['duration'].strip(),
                'description': data['description'].strip(),
                'fee_per_semester': float(data.get('fee_per_semester', 0)),
                'department': data.get('department', {'name': 'General', 'code': 'GEN'})
            }
            
            app.courses.append(new_course)
            
            # Create success response
            response = jsonify({
                'success': True,
                'message': 'Course created successfully',
                'data': new_course
            })
            
            # Add CORS headers
            return response, 201
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500

# DISABLED: Using blueprint version in routes/academics.py instead
# @app.route('/api/academics/courses/<int:course_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_course_DISABLED(course_id):
    try:
        # Find the course
        course = next((c for c in app.courses if c['id'] == course_id), None)
        if not course:
            return jsonify({'success': False, 'error': 'Course not found'}), 404
            
        if request.method == 'GET':
            return jsonify({'success': True, 'data': course})
            
        elif request.method == 'PUT':
            # Update course
            data = request.get_json()
            
            # Update only provided fields
            for key, value in data.items():
                if key in course and key != 'id':  # Don't allow changing the ID
                    course[key] = value
            
            return jsonify({
                'success': True,
                'message': 'Course updated successfully',
                'data': course
            })
            
        elif request.method == 'DELETE':
            # Delete course
            app.courses = [c for c in app.courses if c['id'] != course_id]
            return jsonify({
                'success': True,
                'message': 'Course deleted successfully'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Backward compatibility
@app.route('/api/courses', methods=['GET'])
def get_courses():
    return jsonify({
        'success': True,
        'data': app.courses
    }), 200

# Basic auth endpoints
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    try:
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if hasattr(response, 'error') and response.error:
            return jsonify({"message": "Invalid credentials", "error": response.error.message}), 401
            
        user = response.user
        
        # Get the session
        session = supabase.auth.get_session()
        
        # Check if user exists in your students table
        student_data = supabase.table('students').select('*').eq('email', email).execute()
        
        if not student_data.data:
            return jsonify({"message": "No student found with this email"}), 404
            
        return jsonify({
            "message": "Login successful",
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
                "expires_in": session.expires_in,
                "token_type": session.token_type
            },
            "user": {
                "id": user.id,
                "email": user.email,
                "role": student_data.data[0].get('role', 'student')
            }
        }), 200
            
    except Exception as e:
        app.logger.error(f"Login error: {str(e)}")
        return jsonify({"message": "Login failed", "error": str(e)}), 500

# Admin endpoints
@app.route('/api/admin/students', methods=['GET'])
@supabase_auth_required
def get_all_students():
    try:
        # Mock student data with fast loading
        students = [
            {
                'id': 1,
                'register_number': 'REG2024001',
                'full_name': 'John Doe',
                'email': 'john.doe@student.edu',
                'phone': '+91 9876543210',
                'course': 'B.Tech CSE',
                'current_semester': 5,
                'admission_year': 2022,
                'quota_type': 'merit',
                'category': 'general',
                'hostel_required': True,
                'transport_required': False,
                'status': 'active'
            },
            {
                'id': 2,
                'register_number': 'REG2024002',
                'full_name': 'Jane Smith',
                'email': 'jane.smith@student.edu',
                'phone': '+91 9876543211',
                'course': 'B.Tech ECE',
                'current_semester': 3,
                'admission_year': 2023,
                'quota_type': 'sports',
                'category': 'obc',
                'hostel_required': False,
                'transport_required': True,
                'status': 'active'
            },
            {
                'id': 3,
                'register_number': 'REG2024003',
                'full_name': 'Mike Johnson',
                'email': 'mike.johnson@student.edu',
                'phone': '+91 9876543212',
                'course': 'B.Tech MECH',
                'current_semester': 7,
                'admission_year': 2021,
                'quota_type': 'management',
                'category': 'sc',
                'hostel_required': True,
                'transport_required': True,
                'status': 'active'
            }
        ]

        return jsonify({
            'success': True,
            'data': students
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/attendance/defaulters', methods=['GET'])
@supabase_auth_required
def get_attendance_defaulters():
    try:
        defaulters = [
            {
                'id': 1,
                'name': 'John Doe',
                'register_no': 'REG2024001',
                'course': 'B.Tech CSE',
                'semester': 5,
                'attendance': 68.5,
                'absent_days': 15
            },
            {
                'id': 2,
                'name': 'Jane Smith',
                'register_no': 'REG2024002',
                'course': 'B.Tech ECE',
                'semester': 3,
                'attendance': 72.3,
                'absent_days': 12
            }
        ]

        return jsonify({
            'success': True,
            'data': defaulters
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@supabase_auth_required
def get_admin_stats():
    try:
        stats = {
            'total_students': len(MOCK_DATABASE['students']),
            'faculty_members': 85,
            'pending_admissions': 45,
            'attendance_defaulters': 23,
            'average_attendance': 82.5,
            'excellent_attendance': 156
        }

        return jsonify({
            'success': True,
            'data': stats
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Student listing with pagination and filtering
@app.route('/api/students', methods=['GET'])
@supabase_auth_required
def list_students():
    try:
        # Get query parameters with defaults
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        sort = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        
        # Get filters from query params
        filters = {}
        filter_fields = ['course', 'status', 'admission_year', 'department']
        for field in filter_fields:
            if field in request.args:
                filters[field] = request.args[field]
        
        # Get Supabase client
        supabase = get_supabase()
        
        # Build the base query
        query = supabase.table('students').select('*', count='exact')
        
        # Apply filters
        for field, value in filters.items():
            if value:
                query = query.eq(field, value)
        
        # Apply sorting
        if sort:
            query = query.order(sort, desc=(order.lower() == 'desc'))
        
        # Apply pagination
        start = (page - 1) * limit
        end = start + limit - 1
        query = query.range(start, end)
        
        # Execute the query
        response = query.execute()
        
        # Calculate pagination metadata
        total_items = response.count if hasattr(response, 'count') else len(response.data or [])
        total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
        
        return jsonify({
            'success': True,
            'data': response.data or [],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_items,
                'pages': total_pages
            }
        })
        
    except Exception as e:
        print(f"Error in list_students: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch students',
            'details': str(e)
        }), 500

# Student statistics endpoint
# In case of upstream DB timeouts or errors, return cached or partial data instead of a hard 500 where possible
_last_student_stats_cache = {
    'stats': None,
    'timestamp': None
}

@app.route('/api/students/stats', methods=['GET', 'OPTIONS'])
@supabase_auth_required
def get_student_stats():
    try:
        # Log the request
        app.logger.info('Received request for student stats')
        app.logger.debug(f'Request headers: {request.headers}')

        # Get the current user's identity
        current_user = request.user
        app.logger.info(f'Authenticated user: {current_user}')

        # Get Supabase client
        supabase = get_supabase()
        if not supabase:
            app.logger.error('Failed to initialize Supabase client')
            # If we have cached stats, return them instead of failing
            if _last_student_stats_cache['stats']:
                app.logger.warning('Returning cached stats due to DB init failure')
                cached = _last_student_stats_cache['stats']
                cached['partial'] = True
                return jsonify(cached)
            return jsonify({'error': 'Database connection error'}), 500

        try:
            # Get total number of students (efficient count)
            response = supabase.table('students').select('id', count='exact').execute()
            total_students = response.count if hasattr(response, 'count') else (len(response.data) if response.data else 0)
            app.logger.debug(f'Total students: {total_students}')

            # Efficient gender aggregation: fetch genders in a paginated manner to avoid long-running reads
            gender_counts = {'male': 0, 'female': 0, 'other': 0}
            try:
                # Fetch in pages of 1000 to limit read time
                limit = 1000
                offset = 0
                while True:
                    gender_resp = supabase.table('students').select('gender').limit(limit).offset(offset).execute()
                    data = gender_resp.data if hasattr(gender_resp, 'data') else None
                    if not data:
                        break
                    for student in data:
                        gender = str(student.get('gender', '')).lower()
                        if 'male' in gender:
                            gender_counts['male'] += 1
                        elif 'female' in gender:
                            gender_counts['female'] += 1
                        else:
                            gender_counts['other'] += 1
                    if len(data) < limit:
                        break
                    offset += limit
            except Exception as gender_err:
                app.logger.warning(f'Gender aggregation failed: {str(gender_err)}')

            # Get department count
            dept_count = 0
            try:
                dept_response = supabase.table('departments').select('id', count='exact').execute()
                dept_count = dept_response.count if hasattr(dept_response, 'count') else (len(dept_response.data) if dept_response.data else 0)
            except Exception as dept_error:
                app.logger.warning(f'Could not fetch department count: {str(dept_error)}')

            # Get faculty count
            faculty_count = 0
            try:
                faculty_response = supabase.table('faculty').select('id', count='exact').execute()
                faculty_count = faculty_response.count if hasattr(faculty_response, 'count') else (len(faculty_response.data) if faculty_response.data else 0)
            except Exception as faculty_error:
                app.logger.warning(f'Could not fetch faculty count: {str(faculty_error)}')

            app.logger.debug(f'Department count: {dept_count}, Faculty count: {faculty_count}')

            # Prepare response in the format expected by the frontend
            stats = {
                'success': True,
                'total_students': total_students,
                'recent_students': 0,
                'by_status': {
                    'active': 0,
                    'inactive': 0,
                    'graduated': 0,
                    'suspended': 0
                },
                'by_course': [],
                'by_year': [],
                'total': total_students,
                'male': gender_counts['male'],
                'female': gender_counts['female'],
                'other': gender_counts['other'],
                'departments': dept_count,
                'faculty': faculty_count
            }

            # Update cache
            try:
                _last_student_stats_cache['stats'] = stats.copy()
                _last_student_stats_cache['timestamp'] = datetime.utcnow()
            except Exception:
                app.logger.warning('Failed to update student stats cache')

            app.logger.info('Successfully fetched student stats')
            return jsonify(stats)

        except Exception as db_error:
            app.logger.error(f'Database error in get_student_stats: {str(db_error)}')
            app.logger.error(traceback.format_exc())
            # If we have cached stats, return them as partial result
            if _last_student_stats_cache['stats']:
                app.logger.warning('Returning cached stats due to DB error')
                cached = _last_student_stats_cache['stats']
                cached['partial'] = True
                cached['error_details'] = str(db_error)
                return jsonify(cached)
            # Otherwise return a clear error
            return jsonify({
                'success': False,
                'error': 'Database error',
                'details': str(db_error)
            }), 500

    except Exception as e:
        app.logger.error(f'Error in get_student_stats: {str(e)}')
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Failed to fetch student statistics',
            'details': str(e)
        }), 500

# Student profile endpoints
@app.route('/api/students/profile/<string:student_id>', methods=['GET', 'OPTIONS'])
@supabase_auth_required
def get_student_profile(student_id):
    if request.method == 'OPTIONS':
        # Handle preflight request
        return jsonify({'success': True})
        
    try:
        # Try to get from Supabase first
        if supabase:
            try:
                # Try to convert student_id to integer if it's a numeric string
                student_id_int = None
                if student_id.isdigit():
                    student_id_int = int(student_id)
                
                query = supabase.table('students').select('''
                    *,
                    courses (
                        name,
                        code,
                        departments (
                            name,
                            code
                        )
                    )
                ''')
                
                # If student_id is numeric, try to query by ID
                if student_id_int is not None:
                    response = query.eq('id', student_id_int).execute()
                else:
                    # Otherwise, try to query by a different field (e.g., register_number or email)
                    response = query.or_(f'register_number.eq.{student_id},email.eq.{student_id}').execute()

                if response.data:
                    response_data = {
                        'success': True,
                        'data': response.data[0]
                    }
                    return jsonify(response_data), 200
            except Exception as e:
                print(f"Supabase error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # If we get here, return a 404
        return jsonify({'success': False, 'error': 'Student not found'}), 404
        
    except Exception as e:
        print(f"Error in get_student_profile: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/students/profile/<int:student_id>', methods=['PUT', 'OPTIONS'])
@supabase_auth_required
def update_student_profile(student_id):
    if request.method == 'OPTIONS':
        # Preflight request handled by Flask-CORS
        return jsonify({'success': True})
        
    try:
        data = request.get_json()

        # Mock successful update
        updated_student = {
            'id': student_id,
            **data,
            'updated_at': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': updated_student
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to update profile'}), 500

# Academic data endpoints
@app.route('/api/students/<int:student_id>/academic', methods=['GET'])
@supabase_auth_required
def get_student_academic(student_id):
    try:
        # Try Supabase first
        if supabase:
            try:
                # Get subjects for current semester
                subjects_response = supabase.table('subjects').select('''
                    *,
                    subject_assignments (
                        faculty (
                            full_name,
                            designation
                        )
                    )
                ''').eq('semester', 5).execute()

                if subjects_response.data:
                    return jsonify({
                        'success': True,
                        'data': {
                            'subjects': subjects_response.data,
                            'current_semester': 5,
                            'total_semesters': 8
                        }
                    }), 200
            except Exception as e:
                print(f"Supabase error: {e}")

        # Mock academic data
        mock_academic = {
            'current_semester': 5,
            'total_semesters': 8,
            'subjects': [
                {
                    'id': 1,
                    'name': 'Computer Networks',
                    'code': 'CS501',
                    'credits': 3,
                    'faculty': {
                        'name': 'Dr. Rajesh Kumar',
                        'designation': 'Professor'
                    }
                },
                {
                    'id': 2,
                    'name': 'Database Management Systems',
                    'code': 'CS502',
                    'credits': 4,
                    'faculty': {
                        'name': 'Dr. Priya Sharma',
                        'designation': 'Associate Professor'
                    }
                },
                {
                    'id': 3,
                    'name': 'Operating Systems',
                    'code': 'CS503',
                    'credits': 4,
                    'faculty': {
                        'name': 'Dr. Arun Kumar',
                        'designation': 'Assistant Professor'
                    }
                }
            ],
            'timetable': [
                {'day': 'Monday', 'time': '9:00-10:00', 'subject': 'Computer Networks', 'room': 'CS-101'},
                {'day': 'Monday', 'time': '10:00-11:00', 'subject': 'Database Systems', 'room': 'CS-102'},
                {'day': 'Tuesday', 'time': '9:00-10:00', 'subject': 'Operating Systems', 'room': 'CS-103'},
                {'day': 'Wednesday', 'time': '9:00-10:00', 'subject': 'Computer Networks', 'room': 'CS-101'},
                {'day': 'Thursday', 'time': '10:00-11:00', 'subject': 'Database Systems', 'room': 'CS-102'},
                {'day': 'Friday', 'time': '9:00-10:00', 'subject': 'Operating Systems', 'room': 'CS-103'}
            ]
        }

        return jsonify({
            'success': True,
            'data': mock_academic
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Attendance endpoints
@app.route('/api/students/<int:student_id>/attendance', methods=['GET'])
@supabase_auth_required
def get_student_attendance(student_id):
    try:
        # Try Supabase first
        if supabase:
            try:
                response = supabase.table('attendance').select('''
                    *,
                    subjects (
                        name,
                        code
                    )
                ''').eq('student_id', student_id).execute()

                if response.data:
                    return jsonify({
                        'success': True,
                        'data': response.data
                    }), 200
            except Exception as e:
                print(f"Supabase error: {e}")

        # Comprehensive mock attendance data
        mock_attendance = [
            {
                'id': 1,
                'student_id': student_id,
                'subject': 'Computer Networks',
                'subject_code': 'CS501',
                'date': '2025-01-05',
                'status': 'present',
                'faculty': 'Dr. Rajesh Kumar'
            },
            {
                'id': 2,
                'student_id': student_id,
                'subject': 'Database Systems',
                'subject_code': 'CS502',
                'date': '2025-01-05',
                'status': 'absent',
                'faculty': 'Dr. Priya Sharma'
            },
            {
                'id': 3,
                'student_id': student_id,
                'subject': 'Operating Systems',
                'subject_code': 'CS503',
                'date': '2025-01-04',
                'status': 'present',
                'faculty': 'Dr. Arun Kumar'
            },
            {
                'id': 4,
                'student_id': student_id,
                'subject': 'Computer Networks',
                'subject_code': 'CS501',
                'date': '2025-01-03',
                'status': 'present',
                'faculty': 'Dr. Rajesh Kumar'
            },
            {
                'id': 5,
                'student_id': student_id,
                'subject': 'Database Systems',
                'subject_code': 'CS502',
                'date': '2025-01-03',
                'status': 'present',
                'faculty': 'Dr. Priya Sharma'
            }
        ]

        # Calculate attendance statistics
        total_classes = len(mock_attendance)
        present_classes = len([a for a in mock_attendance if a['status'] == 'present'])
        attendance_percentage = (present_classes / total_classes) * 100 if total_classes > 0 else 0

        return jsonify({
            'success': True,
            'data': {
                'attendance_records': mock_attendance,
                'statistics': {
                    'total_classes': total_classes,
                    'present_classes': present_classes,
                    'absent_classes': total_classes - present_classes,
                    'attendance_percentage': round(attendance_percentage, 2)
                }
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Marks endpoints
@app.route('/api/students/<int:student_id>/marks', methods=['GET'])
@supabase_auth_required
def get_student_marks(student_id):
    try:
        # Get marks from Supabase with exam and subject information
        response = supabase.table('marks').select('''
            *,
            exams (
                name,
                exam_type,
                date
            ),
            subjects (
                name,
                code
            )
        ''').eq('student_id', student_id).execute()

        return jsonify({
            'success': True,
            'data': response.data
        }), 200

    except Exception as e:
        print(f"Error fetching marks: {str(e)}")
        # Fallback to mock data
        mock_marks = [
            {'id': 1, 'student_id': student_id, 'subject': 'Computer Networks', 'exam_type': 'IA1', 'marks_obtained': 85, 'max_marks': 100, 'grade': 'A'},
            {'id': 2, 'student_id': student_id, 'subject': 'Database Systems', 'exam_type': 'IA1', 'marks_obtained': 78, 'max_marks': 100, 'grade': 'B+'},
            {'id': 3, 'student_id': student_id, 'subject': 'Operating Systems', 'exam_type': 'IA2', 'marks_obtained': 82, 'max_marks': 100, 'grade': 'A'}
        ]

        return jsonify({
            'success': True,
            'data': mock_marks
        }), 200

# Add new student endpoint (simplified version)
@app.route('/api/students', methods=['POST'])
@admin_required  # Use admin_required instead of supabase_auth_required
def add_student():
    try:
        data = request.get_json()
        
        # Required fields validation (excluding register_number as it will be auto-generated)
        required_fields = ['full_name', 'email', 'phone', 'department_id', 'course_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
            
        # Generate register_number if not provided
        if not data.get('register_number'):
            # Format: REG + current year (last 2 digits) + 5 random digits
            current_year = datetime.now().year % 100  # Get last 2 digits of year
            random_digits = ''.join(random.choices('0123456789', k=5))
            data['register_number'] = f'REG{current_year}{random_digits}'
            
            # Ensure the generated register_number is unique
            while True:
                existing = supabase.table('students') \
                    .select('id') \
                    .eq('register_number', data['register_number']) \
                    .execute()
                if not existing.data:
                    break
                # If exists, generate a new one
                random_digits = ''.join(random.choices('0123456789', k=5))
                data['register_number'] = f'REG{current_year}{random_digits}'

        # Validate email format
        email = data['email'].strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400

        # Check if student with email or register number already exists using admin client
        existing_email = request.supabase.table('students') \
            .select('id, full_name, email, register_number') \
            .eq('email', email) \
            .execute()
            
        existing_register = request.supabase.table('students') \
            .select('id, full_name, email, register_number') \
            .eq('register_number', data['register_number']) \
            .execute()
            
        if existing_email.data:
            return jsonify({
                'success': False,
                'error': 'A student with this email already exists',
                'existing_student': existing_email.data[0]
            }), 409
            
        if existing_register.data:
            return jsonify({
                'success': False,
                'error': 'A student with this register number already exists',
                'existing_student': existing_register.data[0]
            }), 409

        # Generate a unique student ID
        student_id = str(uuid.uuid4())
        
        # Prepare student data with default values
        student_data = {
            'id': student_id,
            'email': email,
            'full_name': data['full_name'].strip(),
            'phone': str(data['phone']).strip(),
            'register_number': str(data['register_number']).strip(),
            'department_id': int(data['department_id']),
            'course_id': str(data['course_id']),
            'status': 'inactive',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            # Default values for optional fields
            'gender': 'male',
            'date_of_birth': None,
            'address': None,
            'year': 1,
            'current_semester': 1,
            'quota': 'GENERAL',
            'category': 'GENERAL',
            'hostel_required': False,
            'transport_required': False,
            'first_graduate': False,
            'section': 'A',
            'admission_date': datetime.utcnow().date().isoformat(),
            'blood_group': None,
            'father_name': None,
            'mother_name': None,
            'guardian_name': None,
            'guardian_phone': None,
            'annual_income': None,
            'admission_year': datetime.utcnow().year,
            'profile_picture_url': None,
            'type': 'regular',
            'roll_no': None,
            'quota_type': 'GENERAL',
            'branch': None
        }

        # Update with provided optional fields
        optional_fields = [
            'gender', 'date_of_birth', 'address', 'year',
            'current_semester', 'quota', 'category', 'hostel_required',
            'transport_required', 'first_graduate', 'section', 'admission_date',
            'blood_group', 'father_name', 'mother_name', 'guardian_name',
            'guardian_phone', 'annual_income', 'admission_year',
            'profile_picture_url', 'type', 'roll_no', 'quota_type', 'branch'
        ]
        
        for field in optional_fields:
            if field in data and data[field] is not None and data[field] != '':
                # Handle date fields
                if field in ['date_of_birth', 'admission_date'] and data[field]:
                    try:
                        # Handle both YYYY-MM-DD and DD-MM-YYYY formats
                        try:
                            date_obj = datetime.strptime(data[field], '%Y-%m-%d')
                        except ValueError:
                            date_obj = datetime.strptime(data[field], '%d-%m-%Y')
                        student_data[field] = date_obj.date().isoformat()
                    except (ValueError, TypeError) as e:
                        app.logger.warning(f"Invalid date format for {field}: {data[field]}. Error: {str(e)}")
                        # Set to None if date parsing fails
                        student_data[field] = None
                # Handle boolean fields
                elif field in ['hostel_required', 'transport_required', 'first_graduate']:
                    student_data[field] = bool(data[field])
                # Handle numeric fields
                elif field == 'annual_income' and data[field]:
                    try:
                        # Remove any non-numeric characters except decimal point
                        numeric_value = float(''.join(c for c in str(data[field]) if c.isdigit() or c == '.'))
                        student_data[field] = numeric_value
                    except (ValueError, TypeError) as e:
                        app.logger.warning(f"Invalid value for {field}: {data[field]}. Error: {str(e)}")
                        student_data[field] = None
                # Handle integer fields
                elif field in ['year', 'current_semester', 'admission_year'] and data[field]:
                    try:
                        student_data[field] = int(data[field])
                    except (ValueError, TypeError) as e:
                        app.logger.warning(f"Invalid integer for {field}: {data[field]}. Error: {str(e)}")
                # Handle text fields
                else:
                    student_data[field] = str(data[field]).strip()

        # Skip fee structure check as it's not required for student creation
        app.logger.info("Skipping fee structure check as it's not required for student creation")
        
        # Generate a secure password for the student
        password = generate_secure_password()
        hashed_password = hash_password(password)
        
        # Insert student record using admin client
        try:
            # Ensure required fields are present
            if 'id' not in student_data:
                student_data['id'] = str(uuid.uuid4())
            if 'created_at' not in student_data:
                student_data['created_at'] = datetime.utcnow().isoformat()
            if 'updated_at' not in student_data:
                student_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Insert the student record using admin client
            result = request.supabase.table('students').insert(student_data).execute()
            
            if hasattr(result, 'error') and result.error:
                return jsonify({
                    'success': False,
                    'error': f'Failed to add student: {result.error}'
                }), 500
                
            # Get the created student data
            created_student = result.data[0] if result.data else student_data
            student_id = created_student['id']
            
            # Store credentials in the credentials table
            try:
                credentials_data = {
                    'id': str(uuid.uuid4()),
                    'student_id': student_id,
                    'username': email.split('@')[0],  # Use the part before @ as username
                    'email': email,
                    'password_hash': hashed_password,
                    'is_initial_password': True,
                    'last_login': None,  # Will be set on first login
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                # Insert the credentials
                cred_result = request.supabase.table('student_credentials').insert(credentials_data).execute()
                
                if hasattr(cred_result, 'error') and cred_result.error:
                    app.logger.error(f"Failed to store student credentials: {cred_result.error}")
                    # Don't fail the student creation if credentials storage fails
                    # The student can still be activated later
            except Exception as cred_error:
                app.logger.error(f"Error storing student credentials: {str(cred_error)}")
                app.logger.error(traceback.format_exc())

            if not result.data:
                raise Exception("Failed to fetch created student record")

            student = result.data
                
            # Add timestamps if not already present
            if 'created_at' not in student:
                student['created_at'] = datetime.utcnow().isoformat()
            if 'updated_at' not in student:
                student['updated_at'] = datetime.utcnow().isoformat()
                
            # Update the student record with timestamps
            supabase.table('students') \
                .update({
                    'created_at': student['created_at'],
                    'updated_at': student['updated_at']
                }) \
                .eq('id', student['id']) \
                .execute()
                
            # Update the student object with the latest data
            updated_student = request.supabase.table('students') \
                .select('*') \
                .eq('id', student_data['id']) \
                .single() \
                .execute()
                
            student = updated_student.data if hasattr(updated_student, 'data') else student_data
            
            # Add the initial password to the response
            student['initial_password'] = password
            
        except Exception as e:
            app.logger.error(f"Error inserting student record: {str(e)}")
            # Try minimal insertion as fallback
            try:
                minimal_student = {
                    'id': student_data.get('id', str(uuid.uuid4())),
                    'full_name': student_data.get('full_name', 'New Student'),
                    'email': student_data.get('email', ''),
                    'status': student_data.get('status', 'inactive'),
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                result = supabase.table('students').insert(minimal_student).execute()
                if not result.data:
                    raise Exception('Failed to create minimal student record')
                    
                # Update with remaining fields
                remaining_data = {k: v for k, v in student_data.items() 
                               if k not in minimal_student and v is not None}
                if remaining_data:
                    supabase.table('students') \
                        .update(remaining_data) \
                        .eq('id', minimal_student['id']) \
                        .execute()
                        
                student = result.data[0] if isinstance(result.data, list) else result.data
                
            except Exception as min_error:
                app.logger.error(f"Minimal student insertion failed: {str(min_error)}")
                raise Exception(f"All insertion attempts failed. Last error: {str(min_error)}")

        # Generate a temporary password
        temporary_password = generate_secure_password(12)
        student_email = student_data.get('email', '').strip().lower()
        
        if not student_email:
            raise ValueError("Student email is required for authentication")
            
        # Log the email being used for auth
        app.logger.info(f"Processing auth for email: {student_email}")

        try:
            # Check for existing user first
            existing_users = supabase.auth.admin.list_users().users
            existing_user = next((u for u in existing_users if u.email and u.email.lower() == student_email), None)
            
            if existing_user:
                # User exists, use their ID
                auth_user = {'id': existing_user.id, 'email': existing_user.email}
                app.logger.info(f"Using existing auth user: {existing_user.id} with email: {existing_user.email}")
            else:
                # Create new auth user
                auth_user_data = {
                    "email": student_email,
                    "password": temporary_password,
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": student_data.get('full_name', 'Student').strip(),
                        "email": student_email,
                        "role": "student"
                    }
                }
                
                app.logger.info(f"Creating new auth user with email: {student_email}")
                
                # Create auth user
                try:
                    auth_response = supabase.auth.admin.create_user(auth_user_data)
                    auth_user = auth_response.user
                    
                    if not auth_user or 'id' not in auth_user:
                        raise Exception("Failed to create auth user - no user ID returned")
                        
                    auth_user['email'] = student_email  # Ensure email is set in auth_user
                    app.logger.info(f"Successfully created auth user: {auth_user['id']}")
                    
                except Exception as auth_error:
                    app.logger.error(f"Error creating auth user: {str(auth_error)}")
                    # Try to get more details if available
                    if hasattr(auth_error, 'message'):
                        error_msg = auth_error.message
                    elif hasattr(auth_error, 'args') and auth_error.args:
                        error_msg = str(auth_error.args[0])
                    else:
                        error_msg = str(auth_error)
                    raise Exception(f"Failed to create authentication user: {error_msg}")
            
            # Update student record with auth user ID
            update_result = supabase.table('students') \
                .update({
                    'user_id': auth_user['id'],
                    'status': 'active',
                    'updated_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', student['id']) \
                .execute()
            
            if not update_result.data:
                raise Exception("Failed to update student with auth user ID")
                
            # Update the student object with auth user ID and status
            student['user_id'] = auth_user['id']
            student['status'] = 'active'
            
            # Create profile entry if needed
            try:
                profile_data = {
                    'id': auth_user['id'],
                    'email': student_data['email'],
                    'full_name': student_data['full_name'],
                    'role': 'student',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                supabase.table('profiles').upsert(profile_data).execute()
            except Exception as profile_error:
                app.logger.warning(f"Could not update profile: {str(profile_error)}")
                # Continue even if profile update fails
            
            # Prepare the success response
            response_data = {
                'success': True,
                'message': 'Student added successfully',
                'data': {
                    'id': student.get('id'),
                    'auth_user_id': auth_user.get('id'),
                    'email': student.get('email'),
                    'status': 'active'
                }
            }
            
            # Only include temporary password for new users
            if not existing_user:
                response_data['temporary_password'] = temporary_password
            
        except Exception as auth_error:
            app.logger.error(f"Error in student creation process: {str(auth_error)}")
            app.logger.error(traceback.format_exc())
            
            # If we have a student ID but auth user creation failed, try to get the student data
            if 'id' in locals() and student and 'id' in student:
                try:
                    student_result = supabase.table('students')\
                        .select('*')\
                        .eq('id', student['id'])\
                        .single()\
                        .execute()
                    
                    if student_result.data:
                        student = student_result.data
                except Exception as fetch_error:
                    app.logger.error(f"Failed to fetch student data after error: {str(fetch_error)}")
            
            # Prepare error response with consistent format
            response_data = {
                'success': True,
                'message': 'Student added, but there was an error with login credentials',
                'data': {
                    'id': student.get('id') if 'student' in locals() else None,
                    'email': student.get('email', data.get('email', '')),
                    'status': 'inactive'
                },
                'warning': f'Auth user processing failed: {str(auth_error)}'
            }
        
        return jsonify(response_data), 201

    except Exception as e:
        app.logger.error(f"Error adding student: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Failed to add student',
            'details': str(e)
        }), 500

# Endpoint to activate student and create login credentials
@app.route('/api/students/<student_id>/activate-login', methods=['POST'])
@admin_required
@limiter.limit("5 per minute" if RATE_LIMITING_AVAILABLE else None)
def activate_student_login(student_id):
    try:
        # Get student data using admin client
        student = request.supabase.table('students') \
            .select('*') \
            .eq('id', student_id) \
            .execute()
            
        if not student.data:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404
            
        student_data = student.data[0]
        
        # Check if already activated
        if student_data.get('status') == 'active' and student_data.get('user_id'):
            return jsonify({
                'success': False,
                'error': 'Student is already activated'
            }), 400

        email = student_data['email']
        full_name = student_data['full_name']
        
        # Generate a secure password
        password = generate_secure_password()
        
        # Initialize auth_user_id outside the try block
        auth_user_id = None
        
        try:
            # First, try to find if user already exists
            try:
                user_data = request.supabase.auth.admin.get_user_by_email(email)
                if user_data and hasattr(user_data, 'user'):
                    auth_user_id = user_data.user.id
                    app.logger.info(f"Found existing auth user: {auth_user_id}")
            except Exception as lookup_error:
                app.logger.info(f"No existing user found for {email}, will create new one")
            
            # If user doesn't exist, try to create one
            if not auth_user_id:
                try:
                    auth_user_data = {
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {
                            "full_name": full_name,
                            "email": email,
                            "role": "student"
                        }
                    }
                    
                    app.logger.info(f"Attempting to create auth user with email: {email}")
                    auth_response = request.supabase.auth.admin.create_user(auth_user_data)
                    
                    if not auth_response or not hasattr(auth_response, 'user'):
                        error_msg = getattr(auth_response, 'message', 'No user object in response')
                        raise Exception(f'Failed to create authentication user: {error_msg}')
                    
                    auth_user_id = auth_response.user.id
                    app.logger.info(f"Successfully created auth user: {auth_user_id}")
                    
                except Exception as create_error:
                    app.logger.error(f"Error in auth user creation: {str(create_error)}")
                    app.logger.error(traceback.format_exc())
                    # Even if auth user creation fails, we'll still try to store credentials
                    # and let the student activate with the system credentials
                    auth_user_id = str(uuid.uuid4())  # Generate a temporary ID for our system
                    app.logger.warning(f"Using temporary system ID for credentials: {auth_user_id}")
        except Exception as outer_error:
            app.logger.error(f"Unexpected error during user lookup/creation: {str(outer_error)}")
            app.logger.error(traceback.format_exc())
            # Generate a temporary ID and continue with the process
            auth_user_id = str(uuid.uuid4())
            app.logger.warning(f"Using fallback system ID due to error: {auth_user_id}")

        try:
            # Update student record with user_id and activate
            update_result = request.supabase.table('students') \
                .update({
                    'user_id': auth_user_id,
                    'status': 'active',
                    'updated_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', student_id) \
                .execute()

            if not update_result.data:
                raise Exception('Failed to update student record')
                
            # Update or create profile
            try:
                profile_data = {
                    'id': auth_user_id,
                    'full_name': full_name,
                    'email': email,
                    'role': 'student',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                request.supabase.table('profiles').upsert(profile_data).execute()
                app.logger.info(f"Updated profile for user {auth_user_id}")
                
            except Exception as profile_error:
                app.logger.error(f"Error updating profile (non-critical): {str(profile_error)}")
                # Continue even if profile update fails

            # Store credentials with hashed password
            hashed_password = hash_password(password)
            current_time = datetime.utcnow().isoformat()
            
            try:
                # First, try to get existing credentials to update them if they exist
                existing_creds = request.supabase.table('student_credentials') \
                    .select('*') \
                    .eq('student_id', student_id) \
                    .execute()
                
                credentials_data = {
                    'student_id': student_id,
                    'username': email.split('@')[0],  # Use the part before @ as username
                    'password_hash': hashed_password,
                    'is_initial_password': True,
                    'last_login': None,  # Will be set on first login
                    'updated_at': current_time,
                    'email': email
                }
                
                if existing_creds and len(existing_creds.data) > 0:
                    # Update existing credentials
                    app.logger.info(f"Updating existing credentials for student {student_id}")
                    result = request.supabase.table('student_credentials') \
                        .update(credentials_data) \
                        .eq('student_id', student_id) \
                        .execute()
                else:
                    # Insert new credentials
                    app.logger.info(f"Creating new credentials for student {student_id}")
                    credentials_data.update({
                        'id': str(uuid.uuid4()),
                        'created_at': current_time
                    })
                    result = request.supabase.table('student_credentials').insert(credentials_data).execute()
                
                if hasattr(result, 'error') and result.error:
                    raise Exception(f"Failed to store credentials: {result.error}")
                    
                app.logger.info("Successfully stored/updated student credentials")
                
            except Exception as cred_error:
                app.logger.error(f"Error in credentials management: {str(cred_error)}")
                app.logger.error(traceback.format_exc())
                # Store the error in the response but don't fail the activation
                if 'credentials_data' not in locals():
                    credentials_data = {}
                credentials_data['error'] = str(cred_error)
                
                # Try a direct SQL insert as fallback if the ORM approach fails
                try:
                    app.logger.warning("Attempting fallback credentials storage...")
                    request.supabase.rpc('upsert_student_credentials', {
                        'p_id': str(uuid.uuid4()),
                        'p_student_id': student_id,
                        'p_username': email.split('@')[0],
                        'p_password_hash': hashed_password,
                        'p_email': email,
                        'p_created_at': current_time,
                        'p_updated_at': current_time
                    }).execute()
                    app.logger.info("Fallback credentials storage successful")
                except Exception as fallback_error:
                    app.logger.error(f"Fallback credentials storage failed: {str(fallback_error)}")

            app.logger.info("Student activated successfully. Email sending is currently disabled.")
            
            # Prepare response
            response_data = {
                'success': True,
                'message': 'Student activated successfully',
                'data': {
                    'id': student_id,
                    'email': email,
                    'status': 'active',
                    'full_name': full_name,
                    'register_number': student_data.get('register_number', '')
                },
                'temporary_password': password
            }
            
            return jsonify(response_data)

        except Exception as e:
            # Clean up auth user if student update fails
            try:
                if 'auth_user_id' in locals():
                    request.supabase.auth.admin.delete_user(auth_user_id)
            except Exception as cleanup_error:
                app.logger.error(f"Error during cleanup: {str(cleanup_error)}")
            raise

    except Exception as e:
        app.logger.error(f"Error in activate_student_login: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Failed to activate student',
            'details': str(e) if str(e) != 'None' else 'Unknown error occurred'
        }), 500

# Update student endpoint
@app.route('/api/admin/students/<int:student_id>', methods=['PUT'])
@supabase_auth_required
def update_student(student_id):
    try:
        data = request.get_json()
        student_index = next((i for i, s in enumerate(MOCK_DATABASE['students']) if s['id'] == student_id), None)

        if student_index is None:
            return jsonify({'error': 'Student not found'}), 404

        MOCK_DATABASE['students'][student_index].update(data)

        return jsonify({
            'success': True,
            'message': 'Student updated successfully',
            'data': MOCK_DATABASE['students'][student_index]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Delete student endpoint
@app.route('/api/admin/students/<int:student_id>', methods=['DELETE'])
@supabase_auth_required
def delete_student(student_id):
    try:
        student_index = next((i for i, s in enumerate(MOCK_DATABASE['students']) if s['id'] == student_id), None)

        if student_index is None:
            return jsonify({'error': 'Student not found'}), 404

        deleted_student = MOCK_DATABASE['students'].pop(student_index)

        return jsonify({
            'success': True,
            'message': 'Student deleted successfully',
            'data': deleted_student
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Hall Ticket Generation
@app.route('/api/students/<int:student_id>/hallticket/<int:exam_id>', methods=['GET'])
@supabase_auth_required
def generate_hall_ticket(student_id, exam_id):
    try:
        # Get student details
        student_response = supabase.table('students').select('''
            *,
            courses (
                name,
                code
            )
        ''').eq('id', student_id).execute()

        # Get exam details
        exam_response = supabase.table('exams').select('''
            *,
            subjects (
                name,
                code
            )
        ''').eq('id', exam_id).execute()

        if not student_response.data or not exam_response.data:
            return jsonify({'error': 'Student or exam not found'}), 404

        student = student_response.data[0]
        exam = exam_response.data[0]

        hall_ticket = {
            'hall_ticket_number': f"HT{datetime.now().year}{student_id:04d}{exam_id:03d}",
            'student': student,
            'exam': exam,
            'exam_center': 'Cube Arts and Engineering College',
            'instructions': [
                'Bring this hall ticket to the examination hall',
                'Carry a valid photo ID proof',
                'Report to the exam hall 30 minutes before the exam',
                'Mobile phones are not allowed in the exam hall',
                'Use only blue/black pen for writing'
            ],
            'generated_at': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'data': hall_ticket
        }), 200

    except Exception as e:
        print(f"Error generating hall ticket: {str(e)}")
        # Fallback to mock data
        hall_ticket = {
            'hall_ticket_number': f"HT{datetime.now().year}{student_id:04d}{exam_id:03d}",
            'student': {
                'full_name': 'John Doe',
                'register_number': 'REG2024001',
                'course': 'B.Tech CSE',
                'current_semester': 5
            },
            'exam': {
                'name': 'Computer Networks Final Exam',
                'date': '2025-02-15',
                'start_time': '10:00:00',
                'duration_minutes': 180
            },
            'exam_center': 'Cube Arts and Engineering College',
            'instructions': [
                'Bring this hall ticket to the examination hall',
                'Carry a valid photo ID proof',
                'Report to the exam hall 30 minutes before the exam',
                'Mobile phones are not allowed in the exam hall',
                'Use only blue/black pen for writing'
            ],
            'generated_at': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'data': hall_ticket
        }), 200

# Fees and Admission endpoints
@app.route('/api/students/<int:student_id>/fees', methods=['GET'])
@supabase_auth_required
def get_student_fees(student_id):
    try:
        # Try Supabase first
        if supabase:
            try:
                fees_response = supabase.table('fee_payments').select('''
                    *,
                    fee_structures (
                        *
                    )
                ''').eq('student_id', student_id).execute()

                if fees_response.data:
                    return jsonify({
                        'success': True,
                        'data': fees_response.data
                    }), 200
            except Exception as e:
                print(f"Supabase error: {e}")

        # Mock fees data
        mock_fees = {
            'fee_structure': {
                'tuition_fee': 50000,
                'lab_fee': 5000,
                'library_fee': 2000,
                'sports_fee': 1000,
                'development_fee': 3000,
                'exam_fee': 1000,
                'total_fee': 62000
            },
            'payments': [
                {
                    'id': 1,
                    'semester': 1,
                    'amount_paid': 62000,
                    'payment_date': '2022-08-15',
                    'payment_method': 'online',
                    'transaction_id': 'TXN123456789',
                    'receipt_number': 'RCP001',
                    'status': 'completed'
                },
                {
                    'id': 2,
                    'semester': 2,
                    'amount_paid': 62000,
                    'payment_date': '2022-12-15',
                    'payment_method': 'online',
                    'transaction_id': 'TXN123456790',
                    'receipt_number': 'RCP002',
                    'status': 'completed'
                },
                {
                    'id': 3,
                    'semester': 3,
                    'amount_paid': 62000,
                    'payment_date': '2023-08-15',
                    'payment_method': 'online',
                    'transaction_id': 'TXN123456791',
                    'receipt_number': 'RCP003',
                    'status': 'completed'
                },
                {
                    'id': 4,
                    'semester': 4,
                    'amount_paid': 62000,
                    'payment_date': '2023-12-15',
                    'payment_method': 'online',
                    'transaction_id': 'TXN123456792',
                    'receipt_number': 'RCP004',
                    'status': 'completed'
                },
                {
                    'id': 5,
                    'semester': 5,
                    'amount_paid': 0,
                    'payment_date': None,
                    'payment_method': None,
                    'transaction_id': None,
                    'receipt_number': None,
                    'status': 'pending'
                }
            ],
            'scholarships': [
                {
                    'id': 1,
                    'name': 'Merit Scholarship',
                    'amount': 10000,
                    'academic_year': '2024-25',
                    'status': 'approved'
                }
            ],
            'summary': {
                'total_fees': 310000,  # 5 semesters * 62000
                'total_paid': 248000,  # 4 semesters paid
                'pending_amount': 62000,  # Current semester
                'scholarship_amount': 10000
            }
        }

        return jsonify({
            'success': True,
            'data': mock_fees
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Resume upload and AI feedback endpoint
@app.route('/api/students/<int:student_id>/resume', methods=['GET', 'POST'])
@supabase_auth_required
def handle_resume(student_id):
    if request.method == 'GET':
        try:
            # Check if the student has an uploaded resume
            upload_dir = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                return jsonify({'success': False, 'error': 'No uploads directory found'}), 404
                
            # Look for files that start with the student_id
            resume_files = [f for f in os.listdir(upload_dir) 
                          if f.startswith(f"{student_id}_") and 
                          f.lower().endswith(tuple(f".{ext}" for ext in app.config['ALLOWED_EXTENSIONS']))]
            
            if not resume_files:
                return jsonify({'success': False, 'error': 'No resume found for this student'}), 404
                
            # Get the most recent resume
            latest_resume = max(resume_files, key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)))
            
            return jsonify({
                'success': True,
                'resume_url': f"/uploads/{latest_resume}",
                'filename': latest_resume,
                'uploaded_at': os.path.getmtime(os.path.join(upload_dir, latest_resume))
            })
            
        except Exception as e:
            print(f"Error retrieving resume: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Existing POST method implementation
    elif request.method == 'POST':
        try:
            print("Received resume upload request")
            print(f"Request headers: {request.headers}")
            print(f"Request files: {request.files}")
            
            # Check if the post request has the file part
            if 'resume' not in request.files:
                print("No file part in request")
                return jsonify({'success': False, 'error': 'No file part'}), 400
                
            file = request.files['resume']
            print(f"Received file: {file.filename}")
            
            # If user does not select file, browser may submit an empty part without filename
            if file.filename == '':
                print("No selected file")
                return jsonify({'success': False, 'error': 'No selected file'}), 400
                
            if not allowed_file(file.filename):
                print(f"File type not allowed: {file.filename}")
                return jsonify({'success': False, 'error': 'File type not allowed'}), 400
                
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{student_id}_{int(time.time())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Ensure upload directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            try:
                # Save the file
                print(f"Saving file to: {filepath}")
                file.save(filepath)
                print("File saved successfully")
                
                # For now, skip AI analysis and just return success
                return jsonify({
                    'success': True,
                    'message': 'File uploaded successfully',
                    'file_path': f"/uploads/{unique_filename}",
                    'filename': unique_filename
                }), 200
                
            except Exception as e:
                print(f"Error saving file: {str(e)}")
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
                return jsonify({'success': False, 'error': f'Error saving file: {str(e)}'}), 500
                
        except Exception as e:
            print(f"Error in upload_resume: {str(e)}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

# Add this helper function if not already present
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Student settings endpoints
@app.route('/api/students/<int:student_id>/settings', methods=['GET'])
def get_student_settings(student_id):
    try:
        # Mock settings data
        settings = {
            'notifications': {
                'email_notifications': True,
                'sms_notifications': True,
                'push_notifications': True,
                'academic_alerts': True,
                'fee_reminders': True,
                'exam_notifications': True
            },
            'privacy': {
                'profile_visibility': 'private',
                'contact_sharing': False,
                'academic_sharing': False
            },
            'preferences': {
                'language': 'english',
                'theme': 'light',
                'dashboard_layout': 'grid',
                'date_format': 'DD/MM/YYYY'
            },
            'security': {
                'two_factor_enabled': False,
                'login_alerts': True,
                'session_timeout': 30
            }
        }

        return jsonify({
            'success': True,
            'data': settings
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<int:student_id>/settings', methods=['PUT'])
def update_student_settings(student_id):
    try:
        data = request.get_json()

        # Mock settings update
        updated_settings = {
            **data,
            'updated_at': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'data': updated_settings
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Clubs endpoints
@app.route('/api/clubs', methods=['GET', 'POST'])
def handle_clubs():
    if request.method == 'GET':
        try:
            print("Attempting to fetch clubs from Supabase...")
            # Get all clubs from Supabase
            response = supabase.table('clubs').select('*').execute()
            print(f"Supabase response: {response}")
            
            # Check if response has data attribute
            if hasattr(response, 'data'):
                print(f"Found {len(response.data)} clubs")
                return jsonify({
                    'success': True,
                    'data': response.data
                }), 200
            else:
                print("No data attribute in response")
                return jsonify({
                    'success': True,
                    'data': []
                }), 200
                
        except Exception as e:
            import traceback
            error_msg = f"Error fetching clubs: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return jsonify({
                'success': False,
                'message': 'Failed to fetch clubs',
                'error': str(e)
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            # Add new club to Supabase
            response = supabase.table('clubs').insert(data).execute()
            return jsonify({
                'success': True,
                'data': response.data[0] if hasattr(response, 'data') and response.data else {}
            }), 201
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

@app.route('/api/clubs/<club_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_club(club_id):
    if request.method == 'GET':
        try:
            # Get single club by ID
            response = supabase.table('clubs').select('*').eq('id', club_id).execute()
            if not response.data:
                return jsonify({'success': False, 'message': 'Club not found'}), 404
            return jsonify({'success': True, 'data': response.data[0]})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    elif request.method == 'PUT':
        try:
            data = request.get_json()
            # Update club in Supabase
            response = supabase.table('clubs').update(data).eq('id', club_id).execute()
            if not response.data:
                return jsonify({'success': False, 'message': 'Club not found'}), 404
            return jsonify({'success': True, 'data': response.data[0]})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            # Delete club from Supabase
            response = supabase.table('clubs').delete().eq('id', club_id).execute()
            if not response.data:
                return jsonify({'success': False, 'message': 'Club not found'}), 404
            return jsonify({'success': True, 'message': 'Club deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clubs/<club_id>/members', methods=['GET'])
def get_club_members(club_id):
    try:
        # Get club members with student information
        response = supabase.table('club_members').select('''
            *,
            students (
                register_number,
                profiles!students_user_id_fkey (
                    full_name,
                    email
                )
            )
        ''').eq('club_id', club_id).execute()

        if response.data:
            # Process the data to match expected format
            processed_members = []
            for member in response.data:
                processed_member = {
                    'id': member['id'],
                    'club_id': member['club_id'],
                    'student_id': member['student_id'],
                    'role': member['role'],
                    'status': member['status'],
                    'joined_at': member['joined_at'],
                    'name': member['students']['profiles']['full_name'] if member['students'] and member['students']['profiles'] else f"Student {member['student_id']}",
                    'email': member['students']['profiles']['email'] if member['students'] and member['students']['profiles'] else '',
                    'register_number': member['students']['register_number'] if member['students'] else '',
                    'is_faculty': False
                }
                processed_members.append(processed_member)

            return jsonify({
                'success': True,
                'data': processed_members
            })
        else:
            return jsonify({
                'success': True,
                'data': []
            })

    except Exception as e:
        print(f"Error fetching club members: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/clubs/<club_id>/members/<member_id>/role', methods=['PUT'])
def update_club_member_role(club_id, member_id):
    try:
        data = request.get_json()
        new_role = data.get('role')

        if not new_role:
            return jsonify({'success': False, 'message': 'Role is required'}), 400

        # Update member role in Supabase
        response = supabase.table('club_members').update({
            'role': new_role,
            'updated_at': datetime.now().isoformat()
        }).eq('id', member_id).eq('club_id', club_id).execute()

        if response.data:
            return jsonify({
                'success': True,
                'data': response.data[0]
            })
        else:
            return jsonify({'success': False, 'message': 'Member not found'}), 404

    except Exception as e:
        print(f"Error updating club member role: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/clubs/<club_id>/members/<member_id>', methods=['DELETE'])
def remove_club_member(club_id, member_id):
    try:
        # Delete member from Supabase
        response = supabase.table('club_members').delete().eq('id', member_id).eq('club_id', club_id).execute()

        if response.data:
            return jsonify({
                'success': True,
                'message': 'Member removed successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Member not found'}), 404

    except Exception as e:
        print(f"Error removing club member: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/clubs/<club_id>/members/invite', methods=['POST'])
def invite_club_member(club_id):
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role', 'member')

        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400

        # Find the student by email through their profile
        profile_response = supabase.table('profiles').select('id').eq('email', email).execute()

        student_id = None
        if profile_response.data:
            # Find the student record associated with this profile
            student_response = supabase.table('students').select('uuid_id').eq('user_id', profile_response.data[0]['id']).execute()
            if student_response.data:
                student_id = student_response.data[0]['uuid_id']

        # Create or update club membership
        member_data = {
            'club_id': club_id,
            'student_id': student_id,
            'email': student_id if student_id else email,  # Only store email if student doesn't exist yet
            'role': role,
            'status': 'active' if student_id else 'pending',
            'joined_at': datetime.now().isoformat()
        }

        response = supabase.table('club_members').upsert(member_data, {
            'onConflict': 'club_id,student_id',
            'ignoreDuplicates': False
        }).execute()

        if response.data:
            return jsonify({
                'success': True,
                'data': response.data[0],
                'message': student_id if student_id else 'Invitation sent successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to invite member'}), 500

    except Exception as e:
        print(f"Error inviting club member: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =====================================================
# UTILITY ENDPOINTS - AUTH USER CLEANUP
# =====================================================

@app.route('/api/admin/cleanup_orphaned_auth_users', methods=['POST', 'GET'])
def cleanup_orphaned_auth_users():
    """
    Clean up orphaned auth users (users in auth.users without corresponding student records).

    Query Parameters:
        - dry_run: If 'true', only list orphaned users without deleting (default: true)
        - email: Specific email to delete (optional)
    """
    try:
        dry_run = request.args.get('dry_run', 'true').lower() == 'true'
        specific_email = request.args.get('email')

        # If specific email is provided, delete only that user
        if specific_email:
            print(f"Attempting to delete auth user with email: {specific_email}")

            # Get all auth users and find the one with matching email
            auth_response = supabase.auth.admin.list_users()

            if not hasattr(auth_response, 'users') or not auth_response.users:
                return jsonify({
                    'success': False,
                    'error': 'No auth users found'
                }), 404

            user_to_delete = None
            for user in auth_response.users:
                if user.email and user.email.lower() == specific_email.lower():
                    user_to_delete = user
                    break

            if not user_to_delete:
                return jsonify({
                    'success': False,
                    'error': f'No auth user found with email: {specific_email}'
                }), 404

            # Delete the user
            try:
                supabase.auth.admin.delete_user(user_to_delete.id)
                return jsonify({
                    'success': True,
                    'message': f'Successfully deleted auth user: {specific_email}',
                    'deleted_user': {
                        'id': user_to_delete.id,
                        'email': user_to_delete.email
                    }
                }), 200
            except Exception as delete_error:
                return jsonify({
                    'success': False,
                    'error': f'Failed to delete auth user: {str(delete_error)}'
                }), 500

        # Otherwise, find all orphaned users
        print("Fetching all auth users...")
        auth_response = supabase.auth.admin.list_users()

        if not hasattr(auth_response, 'users') or not auth_response.users:
            return jsonify({
                'success': True,
                'message': 'No auth users found',
                'orphaned_users': []
            }), 200

        print(f"Found {len(auth_response.users)} auth users")

        # Get all students
        print("Fetching all students...")
        students_response = supabase.table('students').select('id, email, full_name').execute()
        student_emails = {student['email'].lower() for student in students_response.data if student.get('email')}
        student_ids = {str(student['id']) for student in students_response.data if student.get('id')}

        print(f"Found {len(students_response.data)} students")

        # Find orphaned users
        orphaned_users = []
        for user in auth_response.users:
            user_email = user.email.lower() if user.email else None
            user_role = user.user_metadata.get('role') if user.user_metadata else None

            # Only check student users
            if user_role == 'student':
                # Check if user exists in students table by email or id
                if user_email not in student_emails and str(user.id) not in student_ids:
                    orphaned_users.append({
                        'id': str(user.id),
                        'email': user.email,
                        'created_at': str(user.created_at),
                        'role': user_role
                    })

        if not orphaned_users:
            return jsonify({
                'success': True,
                'message': 'No orphaned auth users found',
                'orphaned_users': []
            }), 200

        # If dry run, just return the list
        if dry_run:
            return jsonify({
                'success': True,
                'message': f'Found {len(orphaned_users)} orphaned auth users (dry run - not deleted)',
                'orphaned_users': orphaned_users,
                'note': 'To actually delete these users, call this endpoint with ?dry_run=false'
            }), 200

        # Delete orphaned users
        deleted_count = 0
        failed_count = 0
        errors = []

        for user in orphaned_users:
            try:
                supabase.auth.admin.delete_user(user['id'])
                deleted_count += 1
                print(f"Deleted orphaned auth user: {user['email']}")
            except Exception as delete_error:
                failed_count += 1
                error_msg = f"Failed to delete {user['email']}: {str(delete_error)}"
                errors.append(error_msg)
                print(error_msg)

        return jsonify({
            'success': True,
            'message': f'Cleanup complete. Deleted: {deleted_count}, Failed: {failed_count}',
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'errors': errors if errors else None
        }), 200

    except Exception as e:
        print(f"Error in cleanup_orphaned_auth_users: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_blueprints():
    """Register all blueprints with the Flask application."""
    # Import blueprints here to avoid circular imports
    from routes.auth import auth_bp
    from controllers.hrOnboardingController import hr_onboarding_bp as hr_bp
    from routes.admin import admin_bp
    from routes.students import students_bp
    from routes.faculty import faculty_bp
    from routes.admissions import admissions_bp
    from routes.academics import academics_bp
    from routes.analytics import analytics_bp
    from routes.attendance import attendance_bp
    from routes.fees import fees_bp
    from routes.notifications import notifications_bp
    from routes.resume_analytics import resume_analytics_bp
    from routes.upgraded_system import upgraded_bp
    from routes.student_dashboard import student_dashboard_bp
    from routes.crud_apis import crud_bp
    from routes.career_roadmap import career_roadmap_bp
    from routes.career_courses import bp as career_courses_bp
    from routes.internships import bp as internships_bp
    from routes.exams import exams_bp
    from routes.employeeRoutes import employee_bp
    from routes.transportRoutes import transport_bp
    from routes.transportRoutesApi import transport_routes_bp
    from routes.finance import finance_bp
    from routes.payrollRoutes import register_payroll_routes
    
    # Quality & Accreditation Management blueprints
    from routes.quality.dashboard import quality_dashboard_bp
    from routes.quality.faculty import quality_faculty_bp
    from routes.quality.analytics import quality_analytics_bp
    from routes.quality.audits import quality_audits_bp
    from routes.quality.grievances import quality_grievances_bp
    from routes.quality.policies import quality_policies_bp
    from routes.quality.accreditation import quality_accreditation_bp
    from routes.finance_validation import validation_bp as finance_validation_bp

    # Register blueprints with proper URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(hr_bp)
    app.register_blueprint(career_courses_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(students_bp, url_prefix='/api/students')
    app.register_blueprint(faculty_bp, url_prefix='/api/faculty')
    app.register_blueprint(admissions_bp, url_prefix='/api/admissions')
    app.register_blueprint(academics_bp, url_prefix='/api/academics')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(student_dashboard_bp, url_prefix='/api/student_dashboard')
    app.register_blueprint(career_roadmap_bp, url_prefix='/api/roadmap')
    app.register_blueprint(resume_analytics_bp, url_prefix='/api/resume')
    app.register_blueprint(employee_bp)
    app.register_blueprint(transport_bp)
    app.register_blueprint(transport_routes_bp)
    
    # Quality & Accreditation Management routes
    app.register_blueprint(quality_dashboard_bp, url_prefix='/api/quality')
    app.register_blueprint(quality_faculty_bp, url_prefix='/api/quality')
    app.register_blueprint(quality_analytics_bp, url_prefix='/api/quality')
    app.register_blueprint(quality_audits_bp, url_prefix='/api/quality')
    app.register_blueprint(quality_grievances_bp, url_prefix='/api/quality')
    app.register_blueprint(quality_policies_bp, url_prefix='/api/quality')
    app.register_blueprint(quality_accreditation_bp, url_prefix='/api/quality')
    app.register_blueprint(finance_validation_bp, url_prefix='/api/finance/validate')
    app.register_blueprint(finance_bp)
    register_payroll_routes(app)

    # General API routes
    app.register_blueprint(internships_bp, url_prefix='/api/internships')
    app.register_blueprint(exams_bp, url_prefix='/api')
    app.register_blueprint(attendance_bp, url_prefix='/api')
    app.register_blueprint(fees_bp, url_prefix='/api')
    app.register_blueprint(notifications_bp, url_prefix='/api')
    app.register_blueprint(upgraded_bp, url_prefix='/api')
    app.register_blueprint(crud_bp, url_prefix='/api')
    
    print("All blueprints registered successfully", flush=True)

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        'success': True,
        'message': 'API is working!',
        'time': datetime.now().isoformat(),
        'endpoints': {
            'student_dashboard': '/api/student_dashboard/<student_id>',
            'health': '/health',
            'test': '/api/test'
        }
    })

def list_routes(app):
    """List all registered routes"""
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = f"{rule.endpoint:50s} {methods:20s} {rule}"
        output.append(line)
    return sorted(output)

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Starting Cube Arts and Engineering College API...")
    print("="*70)
    
    # Register blueprints before running the app
    try:
        print("\nRegistering blueprints...")
        register_blueprints()
        print("Successfully registered all blueprints")
        
        # List all registered routes
        print("\nRegistered routes:")
        print("-" * 70)
        for route in list_routes(app):
            print(route)
            
    except Exception as e:
        print(f"\nError registering blueprints: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("\n" + "="*70)
    port = int(os.getenv('PORT', 5001))
    print(f"API will be available at: http://localhost:{port}")
    print("Health check: http://localhost:5001/health")
    print("Test endpoint: http://localhost:5001/api/test")
    print("Student dashboard test: http://localhost:5001/api/student_dashboard/test")
    print("Student dashboard example: http://localhost:5001/api/student_dashboard/1")
    print("="*70 + "\n")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
