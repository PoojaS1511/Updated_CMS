from functools import wraps
from flask import Blueprint, request, jsonify, current_app, render_template, make_response, send_file, url_for, g
import os
import logging
import io
import traceback
import pandas as pd  # type: ignore
from datetime import datetime, timedelta
from typing import Optional
from fpdf import FPDF
from xhtml2pdf import pisa
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, cast
from jinja2 import TemplateNotFound
from middleware.auth_middleware import auth_required as original_auth_required, try_authenticate, get_current_user_id
from supabase_client import get_supabase

# Initialize the blueprint
student_dashboard_bp = Blueprint('student_dashboard', __name__)

# Test endpoint (no auth required)
# This endpoint is excluded from authentication in auth_middleware.py
@student_dashboard_bp.route('/test', methods=['GET'])
def test_route():
    """
    Public test endpoint for the student dashboard.
    This endpoint is excluded from authentication for testing purposes.
    In production, this endpoint should be removed or properly secured.
    """
    return jsonify({
        "success": True,
        "message": "Student dashboard test endpoint is working!",
        "status": "active",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "This is a public test endpoint. In production, ensure proper authentication is in place."
    }), 200

# CORS configuration
ALLOWED_ORIGINS = [
    'http://localhost:3000', 
    'http://localhost:3001', 
    'http://127.0.0.1:3000', 
    'http://127.0.0.1:3001'
]

# Create a type variable to preserve function types
F = TypeVar('F', bound=Callable[..., Any])

def auth_required(roles=None):
    """Custom auth_required decorator that uses Supabase authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Debug log the incoming request
            logger.debug(f"[AUTH] Incoming request to {request.path}")
            logger.debug(f"[AUTH] Request headers: {dict(request.headers)}")
            
            # Get the authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logger.warning("[AUTH] No Authorization header found")
                return jsonify({
                    'success': False,
                    'error': 'Authorization header is missing',
                    'message': 'No token provided',
                    'path': request.path,
                    'method': request.method
                }), 401

            # Extract the token (remove 'Bearer ' prefix if present)
            token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
            
            try:
                # Verify the token with Supabase
                supabase = get_supabase()
                user = supabase.auth.get_user(token)
                
                if not user or not user.user:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid token',
                        'message': 'Failed to authenticate with Supabase'
                    }), 401
                
                # Set the current user in the Flask global object
                g.user = {
                    'id': user.user.id,
                    'email': user.user.email,
                    'role': user.user.user_metadata.get('role', 'student')  # Default to 'student' if role not set
                }
                
                # Check roles if required
                if roles:
                    user_roles = user.user.user_metadata.get('roles', [])
                    if isinstance(roles, str):
                        roles = [roles]
                    
                    if not any(role in user_roles for role in roles):
                        return jsonify({
                            'success': False,
                            'error': 'Insufficient permissions',
                            'message': f'Requires one of these roles: {roles}'
                        }), 403
                
                # Call the original function with all its arguments
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f'Authentication error: {str(e)}')
                return jsonify({
                    'success': False,
                    'error': 'Authentication failed',
                    'message': str(e)
                }), 401
                
        return decorated_function
    return decorator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='student_dashboard.log',
    filemode='a'
)

# Initialize logger
logger = logging.getLogger(__name__)

student_dashboard_bp = Blueprint('student_dashboard', __name__)

# Initialize Supabase client (global)
supabase = get_supabase()

def get_supabase_client():
    """Return the initialized global Supabase client"""
    return supabase

def get_student_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get student profile with course and department details"""
    try:
        supabase = get_supabase_client()
        
        # First try to get student by user_id (Supabase Auth ID)
        response = supabase.table('students')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()
            
        if not response.data:
            # If not found by user_id, try by id (assuming user_id might be the student's id)
            response = supabase.table('students')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
                
        if not response.data:
            logger.warning(f"Student not found with user_id/id: {user_id}")
            return None
            
        student = response.data[0]
        # Ensure 'name' field is present for templates
        if not student.get('name'):
            student['name'] = student.get('full_name') or student.get('register_number') or 'Student'
        
        # Get course details if course_id exists
        if student.get('course_id'):
            try:
                course_response = supabase.table('courses')\
                    .select('*, departments(*)')\
                    .eq('id', student['course_id'])\
                    .execute()
                    
                if course_response.data:
                    course = course_response.data[0]
                    student['course_name'] = course.get('name', 'N/A')
                    student['course_code'] = course.get('code', 'N/A')
                    
                    if course.get('departments'):
                        dept = course['departments']
                        student['department_name'] = dept.get('name', 'N/A')
                        student['department_code'] = dept.get('code', 'N/A')
            except Exception as e:
                logger.error(f"Error fetching course details: {str(e)}")
                # Continue without course details if there's an error
                
        return student
        
    except Exception as e:
        logger.error(f"Error in get_student_profile: {str(e)}\n{traceback.format_exc()}")
        return None

def get_student_exams(user_id: str, exam_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Get exams for student's course, or specific exam if exam_id is provided"""
    try:
        supabase = get_supabase_client()
        
        # First get student's course and semester
        student = get_student_profile(user_id)
        if not student:
            logger.warning(f"Student not found: {user_id}")
            return [] if not exam_id else None
            
        # Get current academic year (assuming format: YYYY-YYYY)
        current_year = datetime.now().year
        academic_year = f"{current_year}-{current_year + 1}"
        
        # If no course_id, try to get all exams (with warning)
        if 'course_id' not in student or not student['course_id']:
            logger.warning(f"Student {user_id} has no course_id, fetching all exams")
            query = supabase.table('exams').select('*')
        else:
            # Build the query with course filter
            query = supabase.table('exams')\
                .select('*')\
                .eq('course_id', student['course_id'])
                
            # Add semester filter if available. Accept both 'semester' and 'current_semester'
            student_semester = None
            if 'semester' in student and student.get('semester'):
                student_semester = student.get('semester')
            elif 'current_semester' in student and student.get('current_semester'):
                student_semester = student.get('current_semester')

            if student_semester:
                query = query.eq('semester', student_semester)
                
            # Add academic year filter
            query = query.eq('academic_year', academic_year)
        
        # If specific exam_id is provided, filter by it
        if exam_id:
            query = query.eq('id', exam_id)
            
        # Execute the query
        response = query.execute()
        
        # Process the response
        exams = response.data if hasattr(response, 'data') and response.data else []
        
        # If no exams found, log a warning
        if not exams:
            logger.warning(f"No exams found for student {user_id}")
            return [] if not exam_id else None
            
        # Process each exam to include additional information
        processed_exams = []
        for exam in exams:
            # Add default venue if not present
            if 'venue' not in exam or not exam['venue']:
                exam['venue'] = "Cube Arts & Engineering College, 123 Education Street, Chennai, Tamil Nadu 600001"
                
            # If subject_id exists, get subject details
            if 'subject_id' in exam and exam['subject_id']:
                try:
                    subject_response = supabase.table('subjects')\
                        .select('*')\
                        .eq('id', exam['subject_id'])\
                        .execute()
                        
                    if subject_response.data:
                        subject = subject_response.data[0]
                        exam['subject_name'] = subject.get('name', 'N/A')
                        exam['subject_code'] = subject.get('code', 'N/A')
                except Exception as e:
                    logger.error(f"Error fetching subject details: {str(e)}")
                    exam['subject_name'] = 'N/A'
                    exam['subject_code'] = 'N/A'
            
            processed_exams.append(exam)
            
        # Return single exam if exam_id was provided, otherwise return all
        return processed_exams[0] if exam_id and processed_exams else processed_exams
        
    except Exception as e:
        logger.error(f"Error in get_student_exams: {str(e)}\n{traceback.format_exc()}")
        return [] if not exam_id else None

@student_dashboard_bp.route('/hall-ticket', methods=['GET'], endpoint='get_hall_ticket_route')
def get_hall_ticket():
    """
    Generate and download hall ticket for a student's exam
    Query parameters:
    - exam_id: ID of the exam to generate hall ticket for (required)
    - student_id: ID of the student (optional, for public access)
    - format: 'pdf' or 'html' (default: 'pdf')
    """
    try:
        # Get student_id from query params or from authenticated session
        user_id = request.args.get('student_id')

        # If no student_id in query params, try to get from authenticated session
        if not user_id and hasattr(g, 'user') and g.user:
            user_id = g.user.get('id')

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Student ID is required'
            }), 400
            
        logger.info(f"Hall ticket request received for user_id: {user_id}")
        logger.debug(f"Request args: {request.args}")
        
        exam_id = request.args.get('exam_id')
        if not exam_id:
            error_msg = 'Exam ID is required in query parameters'
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
        logger.info(f"Fetching hall ticket for student {user_id}, exam {exam_id}")
        
        # Get student and exam data
        logger.debug("Fetching student profile...")
        student = get_student_profile(user_id)
        if not student:
            error_msg = f'Student not found with ID: {user_id}'
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 404
            
        logger.debug(f"Found student: {student.get('id')} - {student.get('name')}")
        logger.debug("Fetching exam details...")
        
        # First try to get the specific exam
        exam = get_student_exams(user_id, exam_id)
        
        # If exam not found, try to get all exams and find a match by name or code
        if not exam:
            logger.warning(f"Exam with ID {exam_id} not found, trying to find by name or code")
            all_exams = get_student_exams(user_id) or []
            
            # Log all available exams for debugging
            logger.debug(f"Available exams for student {user_id}: {[{'id': e.get('id'), 'name': e.get('name')} for e in all_exams]}")
            
            # Try to find exam by name or code
            for e in all_exams:
                if str(e.get('id')) == str(exam_id) or e.get('name') == exam_id or e.get('code') == exam_id:
                    exam = e
                    logger.info(f"Found matching exam: {exam}")
                    break
        
        if not exam:
            # If exam is not found in the database, use a lightweight mock fallback
            # so that hall tickets can still be generated for testing/demo purposes.
            logger.warning(f"Exam with ID {exam_id} not found for student {user_id}. Using mock exam fallback.")

            try:
                mock_date = datetime.now().strftime('%Y-%m-%d')
                exam = {
                    'id': exam_id,
                    'name': f'Exam {exam_id}',
                    'code': f'EXAM-{exam_id}',
                    'course_id': student.get('course_id'),
                    'semester': student.get('semester', 1),
                    'date': mock_date,
                    'exam_date': mock_date,
                    'start_time': '10:00:00',
                    'end_time': '13:00:00',
                    'venue': 'Cube Arts & Engineering College, Main Campus',
                    'hall_ticket_available': True
                }
                logger.debug(f"Using mock exam: {exam}")
            except Exception as fallback_err:
                logger.error(f"Failed to construct mock exam fallback: {fallback_err}")
                return jsonify({
                    'success': False,
                    'error': f'Exam not found and mock fallback failed. Exam ID: {exam_id}'
                }), 404
            
        logger.debug(f"Found exam: {exam.get('id')} - {exam.get('name')}")

        # Add student photo URL if available
        student['photo_url'] = f"https://ui-avatars.com/api/?name={student.get('full_name', 'Student')}&size=200&background=random"

        # Format dates and times
        if 'date' in exam and exam['date']:
            try:
                exam['date'] = datetime.strptime(exam['date'], '%Y-%m-%d').strftime('%d-%m-%Y')
            except (ValueError, TypeError):
                exam['date'] = 'N/A'

        # Handle exam_date field as well (fallback)
        if ('date' not in exam or exam['date'] == 'N/A') and 'exam_date' in exam and exam['exam_date']:
            try:
                exam['date'] = datetime.strptime(str(exam['exam_date']), '%Y-%m-%d').strftime('%d-%m-%Y')
            except (ValueError, TypeError):
                exam['date'] = 'N/A'

        if 'start_time' in exam and exam['start_time']:
            try:
                exam['start_time'] = (datetime.strptime(exam['start_time'], '%H:%M:%S')).strftime('%I:%M %p')
            except (ValueError, TypeError):
                exam['start_time'] = 'N/A'

        if 'end_time' in exam and exam['end_time']:
            try:
                exam['end_time'] = (datetime.strptime(exam['end_time'], '%H:%M:%S')).strftime('%I:%M %p')
            except (ValueError, TypeError):
                exam['end_time'] = 'N/A'

        # Add additional fields for the hall ticket template
        if 'venue_code' not in exam or not exam['venue_code']:
            exam['venue_code'] = 'CUBE-01'

        if 'reporting_time' not in exam or not exam['reporting_time']:
            # Calculate reporting time as 30 minutes before start time
            if exam.get('start_time') and exam['start_time'] != 'N/A':
                exam['reporting_time'] = '30 minutes before exam time'
            else:
                exam['reporting_time'] = '1:30 PM'

        # Format date of birth if available
        if 'date_of_birth' in student and student['date_of_birth']:
            try:
                student['date_of_birth'] = datetime.strptime(str(student['date_of_birth']), '%Y-%m-%d').strftime('%d-%m-%Y')
            except (ValueError, TypeError):
                pass
        
        # Get the output format (default to 'pdf')
        output_format = request.args.get('format', 'pdf').lower()
        
        # Ensure the template directory exists
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
        os.makedirs(template_dir, exist_ok=True)
        
                # Render the HTML template. If the template is missing, fall back to a simple inline template
        try:
            html = render_template('hall_ticket.html', student=student, exam=exam)
        except TemplateNotFound:
            logger.warning('hall_ticket.html template not found; using inline fallback template')
            # Build a minimal HTML hall ticket as a fallback
            html = f"""
            <html>
            <head><title>Hall Ticket - {exam.get('name')}</title></head>
            <body style='font-family: Arial, sans-serif;'>
                <h1 style='text-align:center'>Cube Arts & Engineering College</h1>
                <h2 style='text-align:center'>Hall Ticket</h2>
                <hr/>
                <h3>Student</h3>
                <p><strong>Name:</strong> {student.get('name') or student.get('full_name') or 'Student'}</p>
                <p><strong>Register No:</strong> {student.get('register_number','N/A')}</p>
                <h3>Exam</h3>
                <p><strong>Exam:</strong> {exam.get('name')}</p>
                <p><strong>Date:</strong> {exam.get('date')}</p>
                <p><strong>Start Time:</strong> {exam.get('start_time')}</p>
                <p><strong>Venue:</strong> {exam.get('venue')}</p>
                <hr/>
                <p style='font-size:12px;color:#666'>This is a generated hall ticket (fallback template).</p>
            </body>
            </html>
            """
        
        if output_format == 'html':
            return html
            
        # Generate PDF
        pdf_data = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_data)
        
        if pisa_status.err:
            return jsonify({
                'success': False,
                'error': 'Error generating PDF',
                'details': str(pisa_status.err)
            }), 500
            
        pdf_data.seek(0)
        
        # Create response
        response = make_response(pdf_data.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=hall_ticket_{exam_id}.pdf'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating hall ticket: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@student_dashboard_bp.route('/<user_id>/subjects', methods=['GET'], endpoint='get_student_subjects_route')
def get_student_subjects_route(user_id):
    """Get subjects for student's course"""
    try:
        student = get_student_profile(user_id)
        if not student or 'course_id' not in student or 'semester' not in student:
            return jsonify({
                'success': False,
                'error': 'Student course information not found'
            }), 404
            
        subjects_response = supabase.table('subjects')\
            .select('*')\
            .eq('course_id', student['course_id'])\
            .eq('semester', student['semester'])\
            .execute()
            
        return jsonify({
            'success': True,
            'data': subjects_response.data if hasattr(subjects_response, 'data') else []
        })
    except Exception as e:
        logger.error(f"Error fetching student subjects: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch subjects',
            'details': str(e)
        }), 500

@student_dashboard_bp.route('/<user_id>/exams', methods=['GET'], endpoint='get_student_exams_route')
def get_student_exams_route(user_id):
    """Get all exams for student's course"""
    try:
        exams = get_student_exams(user_id)
        return jsonify({
            'success': True,
            'data': exams
        })
    except Exception as e:
        logger.error(f"Error fetching student exams: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch exams',
            'details': str(e)
        }), 500

@student_dashboard_bp.route('/', defaults={'student_id': None}, methods=['GET'])
@student_dashboard_bp.route('/<string:student_id>', methods=['GET'])
@auth_required()
def get_student_dashboard_route(student_id: Optional[str] = None):
    """
    API endpoint to get student dashboard data
    Requires authentication
    """
    try:
        # If no student_id provided, try to get it from the authenticated user
        if not student_id:
            current_user = getattr(g, 'user', None)
            if not current_user:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'No authenticated user found'
                }), 401
            student_id = current_user.get('id')
            if not student_id:
                return jsonify({
                    'success': False,
                    'error': 'Invalid user',
                    'message': 'No student ID found in user data'
                }), 400
        
        # Validate student_id format
        if not isinstance(student_id, str) or not student_id.strip():
            logger.error(f"[AUTH] Invalid student_id format: {student_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid student ID format',
                'message': 'Student ID must be a non-empty string'
            }), 400
            
        # Return a simple response for now
        return jsonify({
            'success': True,
            'message': 'Student dashboard data',
            'student_id': student_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_student_dashboard_route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error in get_student_dashboard_route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500
    
    import time
    start_time = time.time()
    
    try:
        logger.info(f"[PERF] Starting dashboard data fetch for student_id: {student_id}")
        current_user = g.user
        current_user_id = current_user.get('id')
        current_user_role = current_user.get('role')
        
        # Authorization check
        if current_user_role != 'admin' and current_user_id != student_id:
            logger.warning(f"Unauthorized access attempt: User {current_user_id} tried to access dashboard for student {student_id}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'You can only access your own dashboard'
            }), 403
        
        # Get student profile with basic info first
        student = get_student_profile(student_id)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found',
                'student_id': student_id
            }), 404
        
        # Only fetch essential student fields
        essential_student_data = {
            'id': student.get('id'),
            'first_name': student.get('first_name'),
            'last_name': student.get('last_name'),
            'email': student.get('email'),
            'course_id': student.get('course_id'),
            'semester': student.get('semester'),
            'registration_number': student.get('registration_number')
        }
        
        # Get current academic year
        current_year = datetime.now().year
        academic_year = f"{current_year}-{current_year + 1}"
        
        # Optimize fee payments query - only get current academic year by default
        logger.debug(f"[PERF] Fetching fee payments for student_id: {student_id}")
        fee_payments_response = supabase.table('fee_payments') \
            .select('id, amount_paid, payment_date, payment_method, status, receipt_number, ' \
                   'fee_structures(id, name, academic_year, total_amount, due_date)') \
            .eq('student_id', student_id) \
            .eq('fee_structures.academic_year', academic_year) \
            .order('payment_date', desc=True) \
            .limit(10) \
            .execute()
        fee_payments = fee_payments_response.data if hasattr(fee_payments_response, 'data') else []
        
        # Only fetch essential exam data
        logger.debug("[PERF] Fetching current semester exams")
        exams = get_student_exams(student_id)
        
        # Get current semester subjects - only if needed for the UI
        logger.debug("[PERF] Fetching current semester subjects")
        subjects_response = supabase.table('subjects') \
            .select('id, subject_code, subject_name, credits') \
            .eq('course_id', student['course_id']) \
            .eq('semester', student['semester']) \
            .execute()
        subjects = subjects_response.data if hasattr(subjects_response, 'data') else []
        
        # Calculate total fees and paid amount for summary
        total_fees_due = 0
        total_paid = sum(float(payment.get('amount_paid', 0)) for payment in fee_payments)
        
        # Get fee summary
        fee_summary = {
            'total_due': total_fees_due,
            'total_paid': total_paid,
            'balance': total_fees_due - total_paid,
            'recent_payments': fee_payments[:5]  # Only return recent 5 payments
        }
        
        # Log performance
        elapsed_time = time.time() - start_time
        logger.info(f"[PERF] Dashboard data fetched in {elapsed_time:.2f} seconds for student_id: {student_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'student': essential_student_data,
                'exams': exams[:5] if exams else [],  # Only return upcoming 5 exams
                'subjects': subjects,
                'fee_summary': fee_summary,
                'last_updated': datetime.now().isoformat()
            },
            'metadata': {
                'fetch_time': f"{elapsed_time:.2f}s",
                'payment_count': len(fee_payments),
                'exam_count': len(exams) if exams else 0,
                'subject_count': len(subjects)
            }
        })
        
    except Exception as e:
        error_msg = f"Error in get_student_dashboard_route: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to load dashboard',
            'details': str(e),
            'traceback': traceback.format_exc() if current_app.debug else None
        }), 500

# ============================================
# Fee Management Endpoints
# ============================================

@student_dashboard_bp.route('/fee-structures', methods=['GET'], endpoint='get_fee_structures_route')
@auth_required
def get_fee_structures():
    """Get all fee structures"""
    try:
        supabase = get_supabase_client()
        
        # Get query parameters
        department_id = request.args.get('department_id')
        academic_year = request.args.get('academic_year')
        
        # Build query
        query = supabase.table('fee_structures').select('*')
        
        if department_id:
            query = query.eq('department_id', department_id)
        if academic_year:
            query = query.eq('academic_year', academic_year)
            
        # Execute query
        response = query.execute()
        
        return jsonify({
            'success': True,
            'data': response.data if hasattr(response, 'data') else []
        })
        
    except Exception as e:
        logger.error(f"Error getting fee structures: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch fee structures'
        }), 500

@student_dashboard_bp.route('/fee-structures', methods=['POST'], endpoint='create_fee_structure_route')
@auth_required
def create_fee_structure():
    """Create a new fee structure"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'amount', 'department_id', 'academic_year']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
            
        # Get current user ID
        user_id = g.user.get('id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
                
        supabase = get_supabase_client()
        
        # Check if fee structure already exists for this department and year
        existing = supabase.table('fee_structures')\
            .select('*')\
            .eq('department_id', data['department_id'])\
            .eq('academic_year', data['academic_year'])\
            .execute()
            
        if existing.data:
            return jsonify({
                'success': False,
                'error': 'Fee structure already exists for this department and academic year'
            }), 400
            
        # Create new fee structure
        fee_structure = {
            'name': data['name'],
            'amount': float(data['amount']),
            'department_id': int(data['department_id']),
            'academic_year': data['academic_year'],
            'created_by': user_id
        }
        
        # Insert into database
        response = supabase.table('fee_structures')\
            .insert(fee_structure)\
            .execute()
            
        if not response.data:
            raise Exception('Failed to create fee structure')
            
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating fee structure: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create fee structure',
            'details': str(e)
        }), 500

@student_dashboard_bp.route('/fee-payments', methods=['GET'], endpoint='get_fee_payments_route')
def get_fee_payments():
    """Get fee payments for the current student. Allows unauthenticated access when `student_id` query param is provided."""
    try:
        # Try to authenticate if Authorization header present
        auth_result = try_authenticate()
        if isinstance(auth_result, tuple):
            # An error response (jsonify(...), status) - return immediately
            return auth_result

        supabase = get_supabase_client()

        # Determine student id either from token (if authenticated) or from query param
        if auth_result:  # authenticated
            user_id = auth_result.get('id')

            # Get student ID from user ID
            student = supabase.table('students')\
                .select('id')\
                .eq('user_id', user_id)\
                .single()\
                .execute()

            if not student.data:
                return jsonify({
                    'success': False,
                    'error': 'Student not found'
                }), 404

            student_id = student.data['id']
        else:
            # No auth header - require student_id in query params
            student_id = request.args.get('student_id')
            if not student_id:
                return jsonify({'error': 'Authorization header is missing'}), 401

        # Get query parameters
        academic_year = request.args.get('academic_year')
        semester = request.args.get('semester')

        # Build query
        query = supabase.table('fee_payments')\
            .select('*, fee_structures(*, departments(*))')\
            .eq('student_id', student_id)

        if academic_year:
            query = query.eq('academic_year', academic_year)
        if semester:
            query = query.eq('semester', semester)

        # Execute query
        response = query.order('payment_date', desc=True).execute()

        return jsonify({
            'success': True,
            'data': response.data if hasattr(response, 'data') else []
        })

    except Exception as e:
        logger.error(f"Error getting fee payments: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch fee payments'
        }), 500

@student_dashboard_bp.route('/fee-payments', methods=['POST'], endpoint='create_fee_payment_route')
@auth_required
def create_fee_payment():
    """Create a new fee payment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['fee_structure_id', 'amount', 'academic_year', 'semester']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
                
        user_id = g.user.get('id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
                
        supabase = get_supabase_client()
        
        # Get student ID from user ID
        student = supabase.table('students')\
            .select('id, department_id')\
            .eq('user_id', user_id)\
            .single()\
            .execute()
            
        if not student.data:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404
            
        student_id = student.data['id']
        
        # Verify fee structure exists and matches student's department
        fee_structure = supabase.table('fee_structures')\
            .select('*')\
            .eq('id', data['fee_structure_id'])\
            .eq('department_id', student.data['department_id'])\
            .single()\
            .execute()
            
        if not fee_structure.data:
            return jsonify({
                'success': False,
                'error': 'Invalid fee structure for student department'
            }), 400
            
        # Create payment record
        payment = {
            'student_id': student_id,
            'fee_structure_id': data['fee_structure_id'],
            'amount': float(data['amount']),
            'academic_year': data['academic_year'],
            'semester': int(data['semester']),
            'status': 'completed',
            'transaction_id': data.get('transaction_id')
        }
        
        # Insert into database
        response = supabase.table('fee_payments')\
            .insert(payment)\
            .execute()
            
        if not response.data:
            raise Exception('Failed to create payment')
            
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating fee payment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process payment',
            'details': str(e)
        }), 500

@student_dashboard_bp.route('/fee-summary', methods=['GET'], endpoint='get_fee_summary_route')
def get_fee_summary():
    """Get fee summary for the current student. Allows unauthenticated access when `student_id` query param is provided."""
    try:
        supabase = get_supabase_client()

        # Get current academic year
        current_year = datetime.now().year
        academic_year = f"{current_year}-{current_year + 1}"

        # Try to authenticate if Authorization header present
        auth_result = try_authenticate()
        if isinstance(auth_result, tuple):
            return auth_result

        # Determine student source: query param takes precedence
        student_id_param = request.args.get('student_id')
        if student_id_param:
            student = supabase.table('students')\
                .select('id, department_id, current_semester, course_id, user_id')\
                .eq('id', student_id_param)\
                .single()\
                .execute()
        elif auth_result:
            user_id = auth_result.get('id')
            if not user_id:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            student = supabase.table('students')\
                .select('id, department_id, current_semester, course_id, user_id')\
                .eq('user_id', user_id)\
                .single()\
                .execute()
        else:
            # No auth and no student_id -> require auth when student_id not provided
            return jsonify({'error': 'Authorization header is missing'}), 401

        if not student.data:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        student_id = student.data['id']
        department_id = student.data['department_id']
        current_semester = student.data.get('current_semester', 1)

        # Get fee structure for current academic year
        fee_structure_resp = supabase.table('fee_structures')\
            .select('*')\
            .eq('department_id', department_id)\
            .eq('academic_year', academic_year)\
            .execute()

        if not fee_structure_resp.data:
            return jsonify({
                'success': False,
                'error': 'No fee structure found for current academic year'
            }), 404

        # PostgREST can return multiple rows; prefer the first but log if that's the case
        if isinstance(fee_structure_resp.data, list):
            if len(fee_structure_resp.data) > 1:
                logger.warning(f"Multiple fee_structure rows found for department {department_id} and academic_year {academic_year}; using the first row")
            fee_structure_row = fee_structure_resp.data[0]
        else:
            fee_structure_row = fee_structure_resp.data

        # Get total paid amount
        payments = supabase.table('fee_payments')\
            .select('amount')\
            .eq('student_id', student_id)\
            .eq('academic_year', academic_year)\
            .execute()

        total_paid = sum((payment.get('amount') or 0) for payment in (payments.data or []))
        total_fee = fee_structure_row.get('amount', 0)
        balance = total_fee - total_paid

        # Get payment history
        payment_history = supabase.table('fee_payments')\
            .select('*')\
            .eq('student_id', student_id)\
            .order('payment_date', desc=True)\
            .limit(5)\
            .execute()

        return jsonify({
            'success': True,
            'data': {
                'fee_structure': fee_structure_row,
                'total_fee': total_fee,
                'total_paid': total_paid,
                'balance': balance,
                'payment_history': payment_history.data if hasattr(payment_history, 'data') else [],
                'academic_year': academic_year,
                'current_semester': current_semester
            }
        })

    except Exception as e:
        logger.error(f"Error getting fee summary: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch fee summary',
            'details': str(e)
        }), 500

# Removed duplicate get_student_dashboard function - using the one defined earlier in the file
        
        # Get subjects if course_id is available
        if 'course_id' in student and student['course_id']:
            try:
                supabase = get_supabase_client()
                response = supabase.from_('subjects') \
                    .select('*') \
                    .eq('course_id', student['course_id']) \
                    .execute()
                
                if hasattr(response, 'data') and response.data:
                    dashboard_data['subjects'] = response.data
                    logger.debug(f"Found {len(response.data)} subjects for course {student['course_id']}")
            except Exception as e:
                logger.error(f"Error fetching subjects: {str(e)}")
        else:
            logger.warning(f"Student {user_id} has no course_id, skipping subjects")
        
        # Get exams
        try:
            # Get current academic year (YYYY-YYYY format)
            current_year = datetime.now().year
            academic_year = f"{current_year}-{current_year + 1}"
            
            # Build the exam query
            supabase = get_supabase_client()
            
            # Build the query conditions
            query = supabase.from_('exams').select('*')
            
            # Add course filter if available
            if 'course_id' in student and student['course_id']:
                query = query.eq('course_id', student['course_id'])
            
            # Add academic year filter
            query = query.eq('academic_year', academic_year)
            
            # Add semester filter if available
            if 'semester' in student and student['semester']:
                query = query.eq('semester', student['semester'])
            
            try:
                # Execute the query
                response = query.execute()
                
                # Process the response
                if hasattr(response, 'data') and response.data:
                    dashboard_data['exams'] = response.data
                    dashboard_data['hall_ticket_available'] = any(
                        exam.get('hall_ticket_available', False) 
                        for exam in dashboard_data['exams']
                    )
                    logger.debug(f"Found {len(dashboard_data['exams'])} exams for student {user_id}")
                else:
                    logger.warning(f"No exams found for student {user_id}")
                    dashboard_data['exams'] = []
                    dashboard_data['hall_ticket_available'] = False
                    
            except Exception as e:
                logger.error(f"Error executing exam query: {str(e)}")
                logger.error(traceback.format_exc())
                dashboard_data['exams'] = []
                dashboard_data['hall_ticket_available'] = False
                
        except Exception as e:
            logger.error(f"Error fetching exams: {str(e)}")
            logger.error(traceback.format_exc())
        
        logger.info(f"Successfully prepared dashboard data for {user_id}")
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        error_msg = f"Error in get_student_dashboard_route: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': 'Failed to load dashboard',
            'details': str(e),
            'traceback': traceback.format_exc() if current_app.debug else None
        }), 500
