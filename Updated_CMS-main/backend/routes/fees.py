from flask import Blueprint, request, jsonify, g, current_app
from supabase_client import get_supabase
from datetime import datetime, timedelta
from functools import wraps
import uuid
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fees_bp = Blueprint('fees', __name__)
supabase = get_supabase()

def auth_required(roles=None):
    """Custom auth_required decorator that uses Supabase authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': 'Authorization header is missing',
                    'message': 'No token provided'
                }), 401

            # Extract the token (remove 'Bearer ' prefix if present)
            token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
            
            try:
                # Verify the token with Supabase
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

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            current_app.logger.error(f"{f.__name__} error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({
                "success": False, 
                "error": str(e),
                "details": traceback.format_exc() if current_app.debug else None
            }), 500
    return wrapper

# Helper function to validate UUID
def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

# Helper function to get fee structure by ID (supports both UUID and numeric)
def get_fee_structure_by_id(fee_structure_id):
    try:
        # Try UUID first
        try:
            uuid_obj = uuid.UUID(fee_structure_id)
            query = supabase.table('fee_structures').select('*').eq('id', str(uuid_obj))
        except ValueError:
            # Try numeric ID
            query = supabase.table('fee_structures').select('*').eq('id', fee_structure_id)
        
        result = query.single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting fee structure: {str(e)}")
        return None

# Fee Structure Management
@fees_bp.route('/fee-structure', methods=['GET'])
@auth_required(roles=['admin', 'accountant', 'student'])
@handle_errors
def get_fee_structures():
    """
    Get fee structures with optional filtering
    Access: Admin, Accountant, Student (own fees only)
    """
    try:
        query = supabase.table('fee_structures').select('''
            *,
            courses (
                id,
                name,
                code,
                departments (
                    name,
                    code
                )
            )
        ''')
        
        # If user is a student, only show their course fees
        if g.user.get('role') == 'student':
            # Get student's course and semester
            student_data = supabase.table('students') \
                .select('course_id, current_semester') \
                .eq('user_id', g.user['id']) \
                .single() \
                .execute()
                
            if not student_data.data:
                return jsonify({"success": False, "error": "Student data not found"}), 404
                
            query = query.eq('course_id', student_data.data['course_id']) \
                        .eq('semester', student_data.data['current_semester'])
        
        # Add filters if provided
        course_id = request.args.get('course_id')
        if course_id:
            query = query.eq('course_id', course_id)
            
        quota_type = request.args.get('quota_type')
        if quota_type:
            query = query.eq('quota_type', quota_type)
            
        semester = request.args.get('semester')
        if semester:
            query = query.eq('semester', semester)
            
        academic_year = request.args.get('academic_year')
        if academic_year:
            query = query.eq('academic_year', academic_year)
        
        # Only show active fee structures by default
        if request.args.get('include_inactive') != 'true':
            query = query.eq('is_active', True)
        
        result = query.order('created_at', desc=True).execute()
        
        return jsonify({
            "success": True, 
            "data": result.data,
            "count": len(result.data)
        })
        
    except Exception as e:
        logger.error(f"Error getting fee structures: {str(e)}")
        raise

@fees_bp.route('/fee-structure', methods=['POST'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def create_fee_structure():
    """
    Create a new fee structure
    Access: Admin, Accountant
    """
    try:
        data = request.get_json()
        required_fields = ['course_id', 'quota_type', 'semester', 'academic_year']
        
        # Validate required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False, 
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Check if course exists
        course_result = supabase.table('courses') \
            .select('id') \
            .eq('id', data['course_id']) \
            .execute()
            
        if not course_result.data:
            return jsonify({"success": False, "error": "Invalid course_id"}), 400
        
        # Validate quota_type
        valid_quota_types = ['merit', 'management', 'sports', 'nri', 'general']
        if data['quota_type'] not in valid_quota_types:
            return jsonify({
                "success": False, 
                "error": f"Invalid quota_type. Must be one of: {', '.join(valid_quota_types)}"
            }), 400
        
        # Check if fee structure already exists for this combination
        existing = supabase.table('fee_structures') \
            .select('id') \
            .eq('course_id', data['course_id']) \
            .eq('quota_type', data['quota_type']) \
            .eq('semester', data['semester']) \
            .eq('academic_year', data['academic_year']) \
            .execute()
            
        if existing.data:
            return jsonify({
                "success": False, 
                "error": "Fee structure already exists for this combination"
            }), 400
        
        # Prepare fee data
        fee_data = {
            'course_id': data['course_id'],
            'quota_type': data['quota_type'],
            'semester': data['semester'],
            'academic_year': data['academic_year'],
            'tuition_fee': float(data.get('tuition_fee', 0)),
            'lab_fee': float(data.get('lab_fee', 0)),
            'library_fee': float(data.get('library_fee', 0)),
            'sports_fee': float(data.get('sports_fee', 0)),
            'development_fee': float(data.get('development_fee', 0)),
            'exam_fee': float(data.get('exam_fee', 0)),
            'other_fees': float(data.get('other_fees', 0)),
            'is_active': bool(data.get('is_active', True)),
            'created_by': g.user['id'],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Calculate total amount
        fee_data['total_amount'] = sum([
            fee_data['tuition_fee'],
            fee_data['lab_fee'],
            fee_data['library_fee'],
            fee_data['sports_fee'],
            fee_data['development_fee'],
            fee_data['exam_fee'],
            fee_data['other_fees']
        ])
        
        # Insert into database
        result = supabase.table('fee_structures') \
            .insert(fee_data) \
            .execute()
            
        if not result.data:
            return jsonify({
                "success": False, 
                "error": "Failed to create fee structure"
            }), 500
            
        return jsonify({
            "success": True, 
            "message": "Fee structure created successfully",
            "data": result.data[0] if result.data else {}
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating fee structure: {str(e)}")
        raise

@fees_bp.route('/fee-structure/<uuid:fee_structure_id>', methods=['PUT'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def update_fee_structure(fee_structure_id):
    """
    Update an existing fee structure
    Access: Admin, Accountant
    """
    try:
        data = request.get_json()
        
        # Check if fee structure exists
        existing = supabase.table('fee_structures') \
            .select('*') \
            .eq('id', str(fee_structure_id)) \
            .single() \
            .execute()
            
        if not existing.data:
            return jsonify({"success": False, "error": "Fee structure not found"}), 404
            
        # Validate course_id if provided
        if 'course_id' in data:
            course_result = supabase.table('courses') \
                .select('id') \
                .eq('id', data['course_id']) \
                .execute()
                
            if not course_result.data:
                return jsonify({"success": False, "error": "Invalid course_id"}), 400
        
        # Validate quota_type if provided
        if 'quota_type' in data:
            valid_quota_types = ['merit', 'management', 'sports', 'nri', 'general']
            if data['quota_type'] not in valid_quota_types:
                return jsonify({
                    "success": False, 
                    "error": f"Invalid quota_type. Must be one of: {', '.join(valid_quota_types)}"
                }), 400
        
        # Prepare update data
        update_data = {k: v for k, v in data.items() 
                      if k not in ['id', 'created_at', 'created_by', 'total_amount']}
        
        # Recalculate total amount if any fee component is updated
        fee_components = ['tuition_fee', 'lab_fee', 'library_fee', 'sports_fee', 
                         'development_fee', 'exam_fee', 'other_fees']
        
        if any(comp in update_data for comp in fee_components):
            # Get existing values for components not being updated
            for comp in fee_components:
                if comp not in update_data:
                    update_data[comp] = existing.data.get(comp, 0)
                else:
                    update_data[comp] = float(update_data[comp])
            
            # Calculate new total
            update_data['total_amount'] = sum(
                update_data.get(comp, 0) for comp in fee_components
            )
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update in database
        result = supabase.table('fee_structures') \
            .update(update_data) \
            .eq('id', str(fee_structure_id)) \
            .execute()
            
        if not result.data:
            return jsonify({
                "success": False, 
                "error": "Failed to update fee structure"
            }), 500
            
        return jsonify({
            "success": True, 
            "message": "Fee structure updated successfully",
            "data": result.data[0] if result.data else {}
        })
        
    except Exception as e:
        logger.error(f"Error updating fee structure: {str(e)}")
        raise

@fees_bp.route('/fee-structure/<uuid:fee_structure_id>', methods=['DELETE'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def delete_fee_structure(fee_structure_id):
    """
    Delete a fee structure
    Access: Admin, Accountant
    """
    try:
        fee_structure_id_str = str(fee_structure_id)
        
        # Check if fee structure exists
        existing = supabase.table('fee_structures') \
            .select('id') \
            .eq('id', fee_structure_id_str) \
            .execute()
            
        if not existing.data:
            return jsonify({"success": False, "error": "Fee structure not found"}), 404
        
        # Check if there are any payments for this fee structure
        payments = supabase.table('fee_payments') \
            .select('id') \
            .eq('fee_structure_id', fee_structure_id_str) \
            .execute()
            
        if payments.data:
            return jsonify({
                "success": False, 
                "error": "Cannot delete fee structure with existing payments. Mark as inactive instead."
            }), 400
            
        # Delete the fee structure
        result = supabase.table('fee_structures') \
            .delete() \
            .eq('id', fee_structure_id_str) \
            .execute()
            
        if not result.data:
            return jsonify({
                "success": False, 
                "error": "Failed to delete fee structure"
            }), 500
            
        return jsonify({
            "success": True, 
            "message": "Fee structure deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting fee structure: {str(e)}")
        raise

# ===========================================
# PAYMENT PROCESSING ENDPOINTS
# ===========================================

def generate_receipt_number():
    """Generate a unique receipt number"""
    import random
    import string
    
    while True:
        # Format: REC-YYYYMMDD-XXXXX (where X are random alphanumeric chars)
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        receipt_number = f"REC-{date_part}-{random_part}"
        
        # Check if receipt number already exists
        existing = supabase.table('fee_payments') \
            .select('id') \
            .eq('receipt_number', receipt_number) \
            .execute()
            
        if not existing.data:
            return receipt_number

@fees_bp.route('/payments', methods=['POST'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def create_payment():
    """
    Create a new payment record
    Access: Admin, Accountant
    """
    try:
        data = request.get_json()
        required_fields = ['student_id', 'fee_structure_id', 'amount_paid', 'payment_method']
        
        # Validate required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False, 
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
            
        # Check if student exists
        student = supabase.table('students') \
            .select('id, course_id, current_semester') \
            .eq('id', data['student_id']) \
            .single() \
            .execute()
            
        if not student.data:
            return jsonify({"success": False, "error": "Student not found"}), 404
            
        # Get fee structure (handles both UUID and numeric IDs)
        fee_structure = get_fee_structure_by_id(data['fee_structure_id'])
        
        if not fee_structure:
            return jsonify({
                "success": False, 
                "error": "Fee structure not found"
            }), 404
            
        if not fee_structure.get('is_active', True):
            return jsonify({
                "success": False, 
                "error": "Fee structure is not active"
            }), 400
            
        # Validate payment method
        valid_payment_methods = ['cash', 'credit_card', 'debit_card', 'bank_transfer', 'check', 'online_payment']
        if data['payment_method'] not in valid_payment_methods:
            return jsonify({
                "success": False, 
                "error": f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}"
            }), 400
            
        # Validate amount
        try:
            amount_paid = float(data['amount_paid'])
            if amount_paid <= 0:
                raise ValueError("Amount must be greater than zero")
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid amount"}), 400
            
        # Check if payment already exists for this transaction_id (if provided)
        if 'transaction_id' in data and data['transaction_id']:
            existing_payment = supabase.table('fee_payments') \
                .select('id') \
                .eq('transaction_id', data['transaction_id']) \
                .execute()
                
            if existing_payment.data:
                return jsonify({
                    "success": False, 
                    "error": "Payment with this transaction ID already exists"
                }), 400
        
        # Generate receipt number
        receipt_number = generate_receipt_number()
        
        # Prepare payment data
        payment_data = {
            'student_id': data['student_id'],
            'fee_structure_id': fee_structure['id'],  # Use the resolved UUID
            'amount_paid': amount_paid,
            'payment_method': data['payment_method'],
            'payment_date': datetime.utcnow().isoformat(),
            'receipt_number': receipt_number,
            'status': 'completed',
            'academic_year': fee_structure.data['academic_year'],
            'semester': fee_structure.data['semester'],
            'created_by': g.user['id'],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Add optional fields if provided
        optional_fields = ['transaction_id', 'payment_reference', 'notes', 'payment_proof_url']
        for field in optional_fields:
            if field in data:
                payment_data[field] = data[field]
        
        # Insert payment record
        result = supabase.table('fee_payments') \
            .insert(payment_data) \
            .execute()
            
        if not result.data:
            return jsonify({
                "success": False, 
                "error": "Failed to record payment"
            }), 500
            
        # Get the created payment with related data
        created_payment = supabase.table('fee_payments') \
            .select('''
                *,
                students (
                    id,
                    first_name,
                    last_name,
                    registration_number
                ),
                fee_structures (
                    *,
                    courses (
                        name,
                        code
                    )
                )
            ''') \
            .eq('id', result.data[0]['id']) \
            .single() \
            .execute()
            
        return jsonify({
            "success": True, 
            "message": "Payment recorded successfully",
            "data": created_payment.data
        }), 201
        
    except Exception as e:
        logger.error(f"Error recording payment: {str(e)}")
        raise

@fees_bp.route('/payments/<uuid:payment_id>', methods=['GET'])
@auth_required(roles=['admin', 'accountant', 'student'])
@handle_errors
def get_payment(payment_id):
    """
    Get a specific payment by ID
    Access: Admin, Accountant, Student (own payments only)
    """
    try:
        # Get payment with related data
        result = supabase.table('fee_payments') \
            .select('''
                *,
                students (
                    id,
                    first_name,
                    last_name,
                    registration_number
                ),
                fee_structures (
                    *,
                    courses (
                        name,
                        code
                    )
                ),
                users:created_by (
                    id,
                    email
                )
            ''') \
            .eq('id', str(payment_id)) \
            .single() \
            .execute()
            
        if not result.data:
            return jsonify({"success": False, "error": "Payment not found"}), 404
            
        # If user is a student, ensure they can only view their own payments
        if g.user.get('role') == 'student' and result.data.get('student_id') != g.user.get('id'):
            return jsonify({
                "success": False,
                "error": "Not authorized to view this payment"
            }), 403
            
        return jsonify({
            "success": True,
            "data": result.data
        })
        
    except Exception as e:
        logger.error(f"Error fetching payment: {str(e)}")
        raise

@fees_bp.route('/payments/<uuid:payment_id>/receipt', methods=['GET'])
@auth_required(roles=['admin', 'accountant', 'student'])
@handle_errors
def get_payment_receipt(payment_id):
    """
    Generate a receipt for a payment
    Access: Admin, Accountant, Student (own receipts only)
    """
    try:
        # Get payment with related data
        result = supabase.table('fee_payments') \
            .select('''
                *,
                students (
                    id,
                    first_name,
                    last_name,
                    registration_number,
                    email,
                    phone
                ),
                fee_structures (
                    *,
                    courses (
                        name,
                        code,
                        duration_years
                    )
                )
            ''') \
            .eq('id', str(payment_id)) \
            .single() \
            .execute()
            
        if not result.data:
            return jsonify({"success": False, "error": "Payment not found"}), 404
            
        payment = result.data
        
        # If user is a student, ensure they can only view their own receipts
        if g.user.get('role') == 'student' and payment.get('student_id') != g.user.get('id'):
            return jsonify({
                "success": False,
                "error": "Not authorized to view this receipt"
            }), 403
            
        # Prepare receipt data
        receipt_data = {
            "receipt_number": payment['receipt_number'],
            "payment_date": payment['payment_date'],
            "student_name": f"{payment['students']['first_name']} {payment['students']['last_name']}",
            "registration_number": payment['students']['registration_number'],
            "course_name": payment['fee_structures']['courses']['name'],
            "semester": payment['semester'],
            "academic_year": payment['academic_year'],
            "amount_paid": payment['amount_paid'],
            "payment_method": payment['payment_method'].replace('_', ' ').title(),
            "transaction_id": payment.get('transaction_id', 'N/A'),
            "status": payment['status'].title(),
            "payment_details": [
                {"description": "Tuition Fee", "amount": payment['fee_structures']['tuition_fee']},
                {"description": "Lab Fee", "amount": payment['fee_structures']['lab_fee']},
                {"description": "Library Fee", "amount": payment['fee_structures']['library_fee']},
                {"description": "Sports Fee", "amount": payment['fee_structures']['sports_fee']},
                {"description": "Development Fee", "amount": payment['fee_structures']['development_fee']},
                {"description": "Exam Fee", "amount": payment['fee_structures']['exam_fee']},
                {"description": "Other Fees", "amount": payment['fee_structures']['other_fees']}
            ]
        }
        
        # Calculate total amount
        total_amount = sum(item['amount'] for item in receipt_data['payment_details'])
        receipt_data['total_amount'] = total_amount
        
        # In a real implementation, you would generate a PDF receipt here
        # For now, we'll return the receipt data as JSON
        
        return jsonify({
            "success": True,
            "receipt": receipt_data
        })
        
    except Exception as e:
        logger.error(f"Error generating receipt: {str(e)}")
        raise

# ===========================================
# FEE ANALYTICS & REPORTING ENDPOINTS
# ===========================================

@fees_bp.route('/students/<uuid:student_id>/fee-summary', methods=['GET'])
@auth_required(roles=['admin', 'accountant', 'student'])
@handle_errors
def get_student_fee_summary(student_id):
    """
    Get fee summary for a specific student
    Access: Admin, Accountant, Student (own data only)
    """
    try:
        # Check if student exists
        student = supabase.table('students') \
            .select('id, first_name, last_name, registration_number, course_id, current_semester') \
            .eq('id', str(student_id)) \
            .single() \
            .execute()
            
        if not student.data:
            return jsonify({"success": False, "error": "Student not found"}), 404
            
        # Check if user is authorized to view this student's data
        if g.user.get('role') == 'student' and str(student_id) != g.user.get('id'):
            return jsonify({
                "success": False,
                "error": "Not authorized to view this student's fee information"
            }), 403
            
        # Get student's course details
        course = supabase.table('courses') \
            .select('name, code, duration_years') \
            .eq('id', student.data['course_id']) \
            .single() \
            .execute()
            
        if not course.data:
            return jsonify({"success": False, "error": "Course not found"}), 404
            
        # Get all fee structures for the student's course and semester
        fee_structures = supabase.table('fee_structures') \
            .select('*') \
            .eq('course_id', student.data['course_id']) \
            .eq('semester', student.data['current_semester']) \
            .execute()
            
        if not fee_structures.data:
            return jsonify({"success": False, "error": "No fee structure found for this course and semester"}), 404
            
        # Get all payments made by the student
        payments = supabase.table('fee_payments') \
            .select('*') \
            .eq('student_id', str(student_id)) \
            .execute()
            
        # Calculate fee summary
        current_fee_structure = fee_structures.data[0]  # Assuming one fee structure per course/semester
        total_fees = current_fee_structure['total_amount']
        
        total_paid = sum(payment['amount_paid'] for payment in payments.data)
        balance = max(0, total_fees - total_paid)
        
        # Get payment history
        payment_history = []
        for payment in payments.data:
            payment_history.append({
                'receipt_number': payment['receipt_number'],
                'payment_date': payment['payment_date'],
                'amount_paid': payment['amount_paid'],
                'payment_method': payment['payment_method'],
                'status': payment['status']
            })
            
        # Prepare response
        response = {
            "student": {
                "id": student.data['id'],
                "name": f"{student.data['first_name']} {student.data['last_name']}",
                "registration_number": student.data['registration_number'],
                "course": course.data['name'],
                "semester": student.data['current_semester']
            },
            "fee_summary": {
                "total_fees": total_fees,
                "total_paid": total_paid,
                "balance": balance,
                "currency": "INR",
                "last_payment_date": max([p['payment_date'] for p in payments.data]) if payments.data else None,
                "payment_status": "PAID" if balance <= 0 else "PENDING"
            },
            "fee_breakdown": {
                "tuition_fee": current_fee_structure['tuition_fee'],
                "lab_fee": current_fee_structure['lab_fee'],
                "library_fee": current_fee_structure['library_fee'],
                "sports_fee": current_fee_structure['sports_fee'],
                "development_fee": current_fee_structure['development_fee'],
                "exam_fee": current_fee_structure['exam_fee'],
                "other_fees": current_fee_structure['other_fees']
            },
            "payment_history": payment_history
        }
        
        return jsonify({
            "success": True,
            "data": response
        })
        
    except Exception as e:
        logger.error(f"Error generating student fee summary: {str(e)}")
        raise

@fees_bp.route('/fee-analytics/defaulters', methods=['GET'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def get_fee_defaulters():
    """
    Get list of students with pending fees
    Access: Admin, Accountant
    """
    try:
        # Get query parameters
        course_id = request.args.get('course_id')
        semester = request.args.get('semester')
        min_balance = float(request.args.get('min_balance', 0))
        
        # Build the base query
        query = '''
            students (
                id,
                first_name,
                last_name,
                registration_number,
                email,
                phone,
                current_semester,
                courses (
                    name as course_name,
                    code as course_code
                )
            ),
            total_fees: fee_structures!inner (
                total_amount
            ),
            total_paid: fee_payments (
                amount_paid
            )
        '''
        
        # Execute the query
        result = supabase.rpc('get_fee_defaulters', {
            'p_course_id': course_id,
            'p_semester': int(semester) if semester else None,
            'p_min_balance': min_balance
        }).execute()
        
        # Process the results
        defaulters = []
        for row in result.data:
            total_paid = sum(payment['amount_paid'] for payment in row['total_paid'])
            balance = row['total_fees'][0]['total_amount'] - total_paid
            
            if balance > min_balance:
                defaulters.append({
                    'student_id': row['students']['id'],
                    'name': f"{row['students']['first_name']} {row['students']['last_name']}",
                    'registration_number': row['students']['registration_number'],
                    'course': row['students']['courses']['name'],
                    'semester': row['students']['current_semester'],
                    'total_fees': row['total_fees'][0]['total_amount'],
                    'total_paid': total_paid,
                    'balance': balance,
                    'contact': {
                        'email': row['students']['email'],
                        'phone': row['students']['phone']
                    }
                })
        
        # Sort by balance in descending order
        defaulters.sort(key=lambda x: x['balance'], reverse=True)
        
        # Apply pagination
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        total_items = len(defaulters)
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_defaulters = defaulters[start_idx:end_idx]
        
        return jsonify({
            "success": True,
            "data": {
                "defaulters": paginated_defaulters,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_items": total_items,
                    "total_pages": (total_items + per_page - 1) // per_page
                },
                "summary": {
                    "total_defaulters": total_items,
                    "total_outstanding": sum(d['balance'] for d in defaulters)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching fee defaulters: {str(e)}")
        raise

@fees_bp.route('/fee-analytics/collection-report', methods=['GET'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def get_fee_collection_report():
    """
    Generate fee collection report
    Access: Admin, Accountant
    """
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        course_id = request.args.get('course_id')
        payment_method = request.args.get('payment_method')
        
        # Build the base query
        query = supabase.table('fee_payments') \
            .select('''
                *,
                students (
                    id,
                    first_name,
                    last_name,
                    registration_number,
                    courses (
                        name as course_name,
                        code as course_code
                    )
                ),
                fee_structures (
                    *,
                    courses (
                        name as course_name,
                        code as course_code
                    )
                )
            ''')
        
        # Apply filters
        if start_date:
            query = query.gte('payment_date', start_date)
        if end_date:
            # Add one day to include the entire end date
            end_date_dt = datetime.fromisoformat(end_date) + timedelta(days=1)
            query = query.lt('payment_date', end_date_dt.isoformat())
        if course_id:
            query = query.eq('fee_structures.course_id', course_id)
        if payment_method:
            query = query.eq('payment_method', payment_method)
            
        # Execute the query
        result = query.execute()
        
        # Process the results
        payments = result.data
        total_collected = sum(p['amount_paid'] for p in payments)
        
        # Group by payment method
        payment_methods = {}
        for payment in payments:
            method = payment['payment_method']
            if method not in payment_methods:
                payment_methods[method] = 0
            payment_methods[method] += payment['amount_paid']
        
        # Group by course
        courses = {}
        for payment in payments:
            if 'fee_structures' in payment and payment['fee_structures'] and 'courses' in payment['fee_structures']:
                course = payment['fee_structures']['courses']
                course_id = course['id']
                if course_id not in courses:
                    courses[course_id] = {
                        'id': course_id,
                        'name': course['name'],
                        'code': course['code'],
                        'total_collected': 0,
                        'payment_count': 0
                    }
                courses[course_id]['total_collected'] += payment['amount_paid']
                courses[course_id]['payment_count'] += 1
        
        # Prepare response
        response = {
            "summary": {
                "total_collected": total_collected,
                "payment_count": len(payments),
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            },
            "by_payment_method": [
                {
                    "method": method,
                    "amount": amount,
                    "percentage": (amount / total_collected * 100) if total_collected > 0 else 0
                }
                for method, amount in payment_methods.items()
            ],
            "by_course": list(courses.values()),
            "recent_payments": payments[:10]  # Show most recent 10 payments
        }
        
        return jsonify({
            "success": True,
            "data": response
        })
        
    except Exception as e:
        logger.error(f"Error generating fee collection report: {str(e)}")
        raise

# ===========================================
# PAYMENT TRACKING ENDPOINTS
# ===========================================

@fees_bp.route('/payments', methods=['GET'])
@auth_required(roles=['admin', 'accountant', 'student'])
@handle_errors
def get_payments():
    """
    Get payment records with optional filtering
    Access: Admin, Accountant, Student (own payments only)
    """
    try:
        query = supabase.table('fee_payments').select('''
            *,
            students (
                id,
                first_name,
                last_name,
                registration_number
            ),
            fee_structures (
                *,
                courses (
                    name,
                    code
                )
            ),
            users:created_by (
                id,
                email
            )
        ''')
        
        # If user is a student, only show their payments
        if g.user.get('role') == 'student':
            query = query.eq('student_id', g.user.get('id'))
        else:
            # Admins and accountants can filter by student_id
            student_id = request.args.get('student_id')
            if student_id:
                query = query.eq('student_id', student_id)
        
        # Apply other filters
        fee_structure_id = request.args.get('fee_structure_id')
        if fee_structure_id:
            query = query.eq('fee_structure_id', fee_structure_id)
            
        payment_method = request.args.get('payment_method')
        if payment_method:
            query = query.eq('payment_method', payment_method.lower())
            
        status = request.args.get('status')
        if status:
            query = query.eq('status', status.lower())
            
        # Date range filters
        start_date = request.args.get('start_date')
        if start_date:
            try:
                start_date_dt = datetime.fromisoformat(start_date)
                query = query.gte('payment_date', start_date_dt.isoformat())
            except ValueError:
                return jsonify({"success": False, "error": "Invalid start_date format. Use ISO format (YYYY-MM-DD)"}), 400
                
        end_date = request.args.get('end_date')
        if end_date:
            try:
                end_date_dt = datetime.fromisoformat(end_date) + timedelta(days=1)
                query = query.lt('payment_date', end_date_dt.isoformat())
            except ValueError:
                return jsonify({"success": False, "error": "Invalid end_date format. Use ISO format (YYYY-MM-DD)"}), 400
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Get total count for pagination
        count_result = supabase.table('fee_payments') \
            .select('*', count='exact') \
            .match({k: v for k, v in query.params.items() if k in ['student_id', 'fee_structure_id', 'payment_method', 'status']}) \
            .execute()
            
        total_count = count_result.count if hasattr(count_result, 'count') else 0
        
        # Apply pagination
        query = query.range((page - 1) * per_page, page * per_page - 1)
        
        # Execute query with ordering
        result = query.order('payment_date', desc=True).execute()
        
        return jsonify({
            "success": True,
            "data": result.data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching payments: {str(e)}")
        raise
@fees_bp.route('/payments/<uuid:payment_id>', methods=['PUT'])
@auth_required(roles=['admin', 'accountant'])
@handle_errors
def update_payment(payment_id):
    """
    Update a payment record
    Access: Admin, Accountant
    """
    try:
        data = request.get_json()
        
        # Get the payment record first to check if it exists
        existing_payment = supabase.table('fee_payments') \
            .select('*') \
            .eq('id', str(payment_id)) \
            .single() \
            .execute()
            
        if not existing_payment.data:
            return jsonify({"success": False, "error": "Payment not found"}), 404
            
        # Only allow updating specific fields
        allowed_fields = ['amount_paid', 'payment_method', 'transaction_id', 'status', 'notes', 'payment_date']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # Add updated_at timestamp
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update the payment record
        result = supabase.table('fee_payments') \
            .update(update_data) \
            .eq('id', str(payment_id)) \
            .execute()
            
        if not result.data:
            return jsonify({"success": False, "error": "Failed to update payment record"}), 500
            
        # Get the updated payment with related data
        updated_payment = supabase.table('fee_payments') \
            .select('''
                *,
                students (
                    id,
                    first_name,
                    last_name,
                    registration_number
                ),
                fee_structures (
                    *,
                    courses (
                        name,
                        code
                    )
                )
            ''') \
            .eq('id', str(payment_id)) \
            .single() \
            .execute()
            
        return jsonify({
            "success": True, 
            "message": "Payment updated successfully",
            "data": updated_payment.data
        })
        
    except Exception as e:
        logger.error(f"Error updating payment: {str(e)}")
        raise

# Get fee structure by ID (supports both UUID and numeric ID)
@fees_bp.route('/fee-structure/<fee_structure_identifier>', methods=['GET'])
@auth_required(roles=['admin', 'accountant', 'student'])
@handle_errors
def get_fee_structure_by_id_endpoint(fee_structure_identifier):
    """
    Get fee structure by ID (supports both UUID and numeric ID)
    Access: Admin, Accountant, Student (own fees only)
    """
    try:
        # Get fee structure (handles both UUID and numeric IDs)
        fee_structure = get_fee_structure_by_id(fee_structure_identifier)
        
        if not fee_structure:
            return jsonify({
                "success": False,
                "error": "Fee structure not found"
            }), 404
            
        # If user is a student, verify they have access to this fee structure
        if g.user.get('role') == 'student':
            student_data = supabase.table('students') \
                .select('course_id, current_semester') \
                .eq('user_id', g.user['id']) \
                .single() \
                .execute()
                
            if not student_data.data:
                return jsonify({
                    "success": False,
                    "error": "Student data not found"
                }), 404
                
            if (fee_structure.get('course_id') != student_data.data['course_id'] or 
                fee_structure.get('semester') != student_data.data['current_semester']):
                return jsonify({
                    "success": False,
                    "error": "Access denied"
                }), 403
        
        # Get course details
        course_data = supabase.table('courses') \
            .select('id, name, code, departments (name, code)') \
            .eq('id', fee_structure['course_id']) \
            .single() \
            .execute()
            
        fee_structure['course'] = course_data.data if course_data.data else None
        
        return jsonify({
            "success": True,
            "data": fee_structure
        })
        
    except Exception as e:
        logger.error(f"Error getting fee structure: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve fee structure"
        }), 500

# Receipt Management
@fees_bp.route('/receipts/<string:receipt_number>', methods=['GET'])
@handle_errors
def get_receipt(receipt_number):
    """Get receipt details by receipt number"""
    result = supabase.table('fee_payments').select('''
        *,
        students (
            register_number,
            full_name,
            father_name,
            courses (
                name,
                code
            )
        ),
        fee_structure (
            *,
            courses (
                name,
                code
            )
        )
    ''').eq('receipt_number', receipt_number).execute()
    
    if not result.data:
        return jsonify({"success": False, "error": "Receipt not found"}), 404
    
    payment_data = result.data[0]
    
    # Format receipt data
    receipt = {
        'receipt_number': payment_data['receipt_number'],
        'payment_date': payment_data['payment_date'],
        'student_details': {
            'name': payment_data['students']['full_name'],
            'register_number': payment_data['students']['register_number'],
            'father_name': payment_data['students']['father_name'],
            'course': payment_data['students']['courses']['name']
        },
        'fee_details': {
            'semester': payment_data['fee_structure']['semester'],
            'academic_year': payment_data['fee_structure']['academic_year'],
            'quota_type': payment_data['fee_structure']['quota_type'],
            'tuition_fee': payment_data['fee_structure']['tuition_fee'],
            'lab_fee': payment_data['fee_structure']['lab_fee'],
            'library_fee': payment_data['fee_structure']['library_fee'],
            'sports_fee': payment_data['fee_structure']['sports_fee'],
            'development_fee': payment_data['fee_structure']['development_fee'],
            'exam_fee': payment_data['fee_structure']['exam_fee'],
            'other_fees': payment_data['fee_structure']['other_fees'],
            'total_fee': payment_data['fee_structure']['total_fee']
        },
        'payment_details': {
            'amount_paid': payment_data['amount_paid'],
            'payment_method': payment_data['payment_method'],
            'transaction_id': payment_data['transaction_id'],
            'status': payment_data['status']
        },
        'college_details': {
            'name': 'Cube Arts and Engineering College',
            'address': 'College Address, City, State',
            'phone': '+91 9876543210',
            'email': 'info@college.edu'
        }
    }
    
    return jsonify({"success": True, "data": receipt})

# Fee Analytics
@fees_bp.route('/analytics/student/<int:student_id>/fees', methods=['GET'])
@handle_errors
def get_student_fee_analytics(student_id):
    """
    Get comprehensive fee analytics for a student
    Access: Admin, Accountant
    """
    # Get student details
    student_result = supabase.table('students').select('''
        *,
        courses (
            name,
            code,
            total_semesters
        )
    ''').eq('id', student_id).execute()

    if not student_result.data:
        return jsonify({"success": False, "error": "Student not found"}), 404

    student = student_result.data[0]

    # Get all payments for this student
    payments_result = supabase.table('fee_payments').select('''
        *,
        fee_structure (
            *
        )
    ''').eq('student_id', student_id).execute()

    # Get fee structure for the student's course and quota
    fee_structures_result = supabase.table('fee_structure').select('*').eq('course_id', student['course_id']).eq('quota_type', student['quota_type']).execute()

    # Calculate fee summary
    total_fees = 0
    total_paid = 0
    semester_wise_fees = {}

    # Calculate total fees based on fee structure
    for fee_structure in fee_structures_result.data:
        semester = fee_structure['semester']
        semester_fee = fee_structure['total_fee']
        total_fees += semester_fee

        semester_wise_fees[semester] = {
            'semester': semester,
            'total_fee': semester_fee,
            'paid_amount': 0,
            'balance': semester_fee,
            'status': 'pending',
            'payment_date': None,
            'receipt_number': None
        }

    # Update with actual payments
    for payment in payments_result.data:
        total_paid += payment['amount_paid']
        semester = payment['fee_structure']['semester']

        if semester in semester_wise_fees:
            semester_wise_fees[semester]['paid_amount'] += payment['amount_paid']
            semester_wise_fees[semester]['balance'] = semester_wise_fees[semester]['total_fee'] - semester_wise_fees[semester]['paid_amount']
            semester_wise_fees[semester]['status'] = 'paid' if semester_wise_fees[semester]['balance'] <= 0 else 'partial'
            semester_wise_fees[semester]['payment_date'] = payment['payment_date']
            semester_wise_fees[semester]['receipt_number'] = payment['receipt_number']

    # Calculate pending fees
    pending_amount = total_fees - total_paid

    # Get scholarships (if any)
    # This would be implemented if there's a scholarships table
    scholarship_amount = 0

    fee_summary = {
        'student_id': student_id,
        'student_name': student['full_name'],
        'register_number': student['register_number'],
        'course': student['courses']['name'],
        'quota_type': student['quota_type'],
        'current_semester': student['current_semester'],
        'total_semesters': student['courses']['total_semesters'],
        'fee_summary': {
            'total_fees': total_fees,
            'total_paid': total_paid,
            'pending_amount': pending_amount,
            'scholarship_amount': scholarship_amount,
            'net_payable': total_fees - scholarship_amount
        },
        'semester_wise_fees': list(semester_wise_fees.values()),
        'payment_history': payments_result.data
    }

    return jsonify({"success": True, "data": fee_summary})

@fees_bp.route('/analytics/course/<int:course_id>/fees', methods=['GET'])
@handle_errors
def get_course_fee_analytics(course_id):
    """Get fee analytics for a specific course"""
    # Get all students in this course
    students_result = supabase.table('students').select('id, full_name, register_number, quota_type').eq('course_id', course_id).execute()

    if not students_result.data:
        return jsonify({"success": False, "error": "No students found for this course"}), 404

    # Get all payments for students in this course
    student_ids = [student['id'] for student in students_result.data]
    payments_result = supabase.table('fee_payments').select('''
        *,
        students (
            full_name,
            register_number,
            quota_type
        ),
        fee_structure (
            total_fee,
            semester
        )
    ''').in_('student_id', student_ids).execute()

    # Calculate analytics
    total_students = len(students_result.data)
    total_collected = sum([payment['amount_paid'] for payment in payments_result.data])

    # Payment method distribution
    payment_methods = {}
    for payment in payments_result.data:
        method = payment['payment_method']
        payment_methods[method] = payment_methods.get(method, 0) + payment['amount_paid']

    # Quota-wise collection
    quota_wise_collection = {}
    for payment in payments_result.data:
        quota = payment['students']['quota_type']
        quota_wise_collection[quota] = quota_wise_collection.get(quota, 0) + payment['amount_paid']

    # Monthly collection (last 12 months)
    monthly_collection = {}
    for payment in payments_result.data:
        payment_date = datetime.fromisoformat(payment['payment_date'])
        month_key = payment_date.strftime('%Y-%m')
        monthly_collection[month_key] = monthly_collection.get(month_key, 0) + payment['amount_paid']

    analytics = {
        'course_id': course_id,
        'total_students': total_students,
        'total_collected': total_collected,
        'average_per_student': total_collected / total_students if total_students > 0 else 0,
        'payment_method_distribution': payment_methods,
        'quota_wise_collection': quota_wise_collection,
        'monthly_collection': monthly_collection,
        'total_payments': len(payments_result.data)
    }

    return jsonify({"success": True, "data": analytics})

# The get_fee_defaulters function is defined above with route '/fee-analytics/defaulters'
