from flask import Blueprint, request, jsonify, current_app
from supabase_client import get_supabase
import os
from datetime import datetime, timedelta
import uuid
from functools import wraps
from werkzeug.utils import secure_filename

admissions_bp = Blueprint('admissions', __name__)

# Initialize Supabase client
supabase = get_supabase()

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    return wrapper

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'txt'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_resume(file_path):
    """Extract text from resume file"""
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    
    try:
        if file_extension == '.pdf':
            import PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        elif file_extension in ['.doc', '.docx']:
            import docx2txt
            return docx2txt.process(file_path)
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
    except Exception as e:
        current_app.logger.error(f"Error extracting text from resume: {str(e)}")
        return None

def analyze_resume_with_gemini(resume_text):
    """Analyze resume text using Gemini API"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = """
        Analyze the following resume and extract the following information in JSON format:
        {
            "name": "Full name",
            "email": "Email address",
            "phone": "Phone number",
            "education": [{"degree": "", "institution": "", "year": ""}],
            "experience": [{"title": "", "company": "", "duration": "", "description": ""}],
            "skills": [],
            "summary": "Brief professional summary"
        }
        
        Resume:
        """ + resume_text[:15000]  # Limit input size
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        current_app.logger.error(f"Error analyzing resume with Gemini: {str(e)}")
        return None

def generate_application_number():
    """Generate unique application number"""
    year = datetime.now().year
    random_num = str(uuid.uuid4().int)[:4]
    return f"ADM{year}{random_num}"

@admissions_bp.route('/submit', methods=['POST'])
def submit_application():
    """Submit new admission application"""
    try:
        data = request.get_json()
        
        # Generate application number
        application_number = generate_application_number()
        
        # Prepare admission data
        admission_data = {
            'application_number': application_number,
            'full_name': data.get('full_name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'date_of_birth': data.get('date_of_birth'),
            'gender': data.get('gender'),
            'blood_group': data.get('blood_group'),
            'aadhar_number': data.get('aadhar_number'),
            'religion': data.get('religion'),
            'caste': data.get('caste'),
            'community': data.get('community'),
            'father_name': data.get('father_name'),
            'father_phone': data.get('father_phone'),
            'mother_name': data.get('mother_name'),
            'mother_phone': data.get('mother_phone'),
            'guardian_name': data.get('guardian_name'),
            'annual_income': data.get('annual_income'),
            'permanent_address': data.get('permanent_address'),
            'communication_address': data.get('communication_address'),
            'city': data.get('city'),
            'state': data.get('state'),
            'pincode': data.get('pincode'),
            'tenth_board': data.get('tenth_board'),
            'tenth_year': data.get('tenth_year'),
            'tenth_marks': data.get('tenth_marks'),
            'twelfth_board': data.get('twelfth_board'),
            'twelfth_year': data.get('twelfth_year'),
            'twelfth_marks': data.get('twelfth_marks'),
            'group_studied': data.get('group_studied'),
            'medium_of_instruction': data.get('medium_of_instruction'),
            'course_id': data.get('course_id'),
            'shift_preference': data.get('shift_preference'),
            'quota_type': data.get('quota_type'),
            'first_graduate': data.get('first_graduate', False),
            'hostel_required': data.get('hostel_required', False),
            'transport_required': data.get('transport_required', False),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Insert into database
        response = supabase.table('admissions').insert(admission_data).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'application_number': application_number,
                'message': 'Application submitted successfully',
                'data': response.data[0]
            }), 201
        else:
            return jsonify({'error': 'Failed to submit application'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admissions_bp.route('/applications', methods=['GET'])
@handle_errors
def get_applications():
    """Get all admission applications with enhanced filtering"""
    # Get query parameters
    status = request.args.get('status')
    course_id = request.args.get('course_id')
    quota_type = request.args.get('quota_type')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    search = request.args.get('search', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Build query with course information
    query = supabase.table('admissions').select('''
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

    # Apply filters
    if status:
        query = query.eq('status', status)
    if course_id:
        query = query.eq('course_id', course_id)
    if quota_type:
        query = query.eq('quota_type', quota_type)
    if date_from and date_to:
        query = query.gte('created_at', date_from).lte('created_at', date_to)
    if search:
        query = query.or_(f'full_name.ilike.%{search}%,email.ilike.%{search}%,application_number.ilike.%{search}%,phone.ilike.%{search}%')

    # Execute query with pagination
    offset = (page - 1) * limit
    response = query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()

    # Get total count for pagination
    count_query = supabase.table('admissions').select('id', count='exact')
    if status:
        count_query = count_query.eq('status', status)
    if course_id:
        count_query = count_query.eq('course_id', course_id)
    if quota_type:
        count_query = count_query.eq('quota_type', quota_type)
    if date_from and date_to:
        count_query = count_query.gte('created_at', date_from).lte('created_at', date_to)
    if search:
        count_query = count_query.or_(f'full_name.ilike.%{search}%,email.ilike.%{search}%,application_number.ilike.%{search}%,phone.ilike.%{search}%')

    count_response = count_query.execute()
    total_count = count_response.count

    return jsonify({
        'success': True,
        'data': response.data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'pages': (total_count + limit - 1) // limit
        }
    })

@admissions_bp.route('/applications/<int:application_id>', methods=['GET'])
@handle_errors
def get_application(application_id):
    """Get specific admission application with course details"""
    response = supabase.table('admissions').select('''
        *,
        courses (
            id,
            name,
            code,
            fee_per_semester,
            departments (
                name,
                code
            )
        )
    ''').eq('id', application_id).execute()

    if not response.data:
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    return jsonify({
        'success': True,
        'data': response.data[0]
    })

@admissions_bp.route('/applications/<int:application_id>/status', methods=['PUT'])
@handle_errors
def update_application_status(application_id):
    """Update admission application status with enhanced workflow"""
    data = request.get_json()

    new_status = data.get('status')
    reviewed_by = data.get('reviewed_by')
    remarks = data.get('remarks', '')

    if not new_status:
        return jsonify({'success': False, 'error': 'Status is required'}), 400

    if new_status not in ['pending', 'approved', 'rejected', 'waitlisted']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    # Get the current application
    current_app_response = supabase.table('admissions').select('*').eq('id', application_id).execute()
    if not current_app_response.data:
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    current_application = current_app_response.data[0]

    update_data = {
        'status': new_status,
        'reviewed_by': reviewed_by,
        'remarks': remarks,
        'reviewed_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    response = supabase.table('admissions').update(update_data).eq('id', application_id).execute()

    if response.data:
        # If approved, create student record
        if new_status == 'approved':
            student_creation_result = create_student_from_admission(response.data[0])
            if not student_creation_result['success']:
                return jsonify({
                    'success': False,
                    'error': f'Application approved but failed to create student record: {student_creation_result["error"]}'
                }), 500

        return jsonify({
            'success': True,
            'message': f'Application {new_status} successfully',
            'data': response.data[0]
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to update application'}), 400

def create_student_from_admission(admission_data):
    """Create student record from approved admission with enhanced error handling"""
    try:
        # Check if student already exists for this admission
        existing_student = supabase.table('students').select('id').eq('email', admission_data['email']).execute()
        if existing_student.data:
            return {'success': False, 'error': 'Student record already exists for this email'}

        # Get course information for register number generation
        course_response = supabase.table('courses').select('code').eq('id', admission_data['course_id']).execute()
        if not course_response.data:
            return {'success': False, 'error': 'Course not found'}

        course_code = course_response.data[0]['code']

        # Generate unique register number
        year = datetime.now().year
        # Get count of students in this course for sequential numbering
        student_count = supabase.table('students').select('id', count='exact').eq('course_id', admission_data['course_id']).execute().count or 0
        register_number = f"{year}{course_code}{(student_count + 1):03d}"

        # Check if register number already exists (just in case)
        existing_reg = supabase.table('students').select('id').eq('register_number', register_number).execute()
        if existing_reg.data:
            # Fallback to UUID-based register number
            random_num = str(uuid.uuid4().int)[:4]
            register_number = f"{year}{course_code}{random_num}"

        # Create student record with all required fields
        student_data = {
            'register_number': register_number,
            'full_name': admission_data['full_name'],
            'email': admission_data['email'],
            'phone': admission_data['phone'],
            'course_id': admission_data['course_id'],
            'admission_year': datetime.now().year,
            'current_semester': 1,
            'quota_type': admission_data['quota_type'],
            'date_of_birth': admission_data['date_of_birth'],
            'gender': admission_data['gender'],
            'blood_group': admission_data.get('blood_group'),
            'aadhar_number': admission_data.get('aadhar_number'),
            'religion': admission_data.get('religion'),
            'caste': admission_data.get('caste'),
            'community': admission_data.get('community'),
            'father_name': admission_data.get('father_name'),
            'father_phone': admission_data.get('father_phone'),
            'mother_name': admission_data.get('mother_name'),
            'mother_phone': admission_data.get('mother_phone'),
            'guardian_name': admission_data.get('guardian_name'),
            'annual_income': admission_data.get('annual_income'),
            'permanent_address': admission_data.get('permanent_address'),
            'communication_address': admission_data.get('communication_address'),
            'city': admission_data.get('city'),
            'state': admission_data.get('state'),
            'pincode': admission_data.get('pincode'),
            'tenth_board': admission_data.get('tenth_board'),
            'tenth_year': admission_data.get('tenth_year'),
            'tenth_marks': admission_data.get('tenth_marks'),
            'twelfth_board': admission_data.get('twelfth_board'),
            'twelfth_year': admission_data.get('twelfth_year'),
            'twelfth_marks': admission_data.get('twelfth_marks'),
            'group_studied': admission_data.get('group_studied'),
            'medium_of_instruction': admission_data.get('medium_of_instruction'),
            'first_graduate': admission_data.get('first_graduate', False),
            'hostel_required': admission_data.get('hostel_required', False),
            'transport_required': admission_data.get('transport_required', False),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # Insert student record
        student_response = supabase.table('students').insert(student_data).execute()

        if student_response.data:
            return {'success': True, 'student_id': student_response.data[0]['id'], 'register_number': register_number}
        else:
            return {'success': False, 'error': 'Failed to create student record in database'}

    except Exception as e:
        print(f"Error creating student record: {e}")
        return {'success': False, 'error': str(e)}

@admissions_bp.route('/courses', methods=['GET'])
def get_courses():
    """Get all available courses"""
    try:
        response = supabase.table('courses').select("""
            id,
            name,
            code,
            fee_per_semester,
            departments (
                id,
                name,
                code
            )
        """).execute()
        
        return jsonify({
            'success': True,
            'data': response.data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admissions_bp.route('/stats', methods=['GET'])
@handle_errors
def get_admission_stats():
    """Get comprehensive admission statistics"""
    # Get total applications
    total_response = supabase.table('admissions').select('id', count='exact').execute()
    total_applications = total_response.count or 0

    # Get applications by status
    pending_response = supabase.table('admissions').select('id', count='exact').eq('status', 'pending').execute()
    pending_applications = pending_response.count or 0

    approved_response = supabase.table('admissions').select('id', count='exact').eq('status', 'approved').execute()
    approved_applications = approved_response.count or 0

    rejected_response = supabase.table('admissions').select('id', count='exact').eq('status', 'rejected').execute()
    rejected_applications = rejected_response.count or 0

    waitlisted_response = supabase.table('admissions').select('id', count='exact').eq('status', 'waitlisted').execute()
    waitlisted_applications = waitlisted_response.count or 0

    # Get course-wise applications
    course_wise_response = supabase.table('admissions').select('''
        course_id,
        courses (
            name,
            code
        )
    ''').execute()

    course_wise_stats = {}
    for app in course_wise_response.data:
        course_name = app['courses']['name'] if app['courses'] else 'Unknown'
        course_wise_stats[course_name] = course_wise_stats.get(course_name, 0) + 1

    # Get quota-wise applications
    quota_wise_response = supabase.table('admissions').select('quota_type').execute()
    quota_wise_stats = {}
    for app in quota_wise_response.data:
        quota = app['quota_type'] or 'Not specified'
        quota_wise_stats[quota] = quota_wise_stats.get(quota, 0) + 1

    # Get recent applications (last 7 days)
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent_response = supabase.table('admissions').select('id', count='exact').gte('created_at', seven_days_ago).execute()
    recent_applications = recent_response.count or 0

    # Calculate rates
    approval_rate = (approved_applications / total_applications * 100) if total_applications > 0 else 0
    rejection_rate = (rejected_applications / total_applications * 100) if total_applications > 0 else 0

    return jsonify({
        'success': True,
        'data': {
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'approved_applications': approved_applications,
            'rejected_applications': rejected_applications,
            'waitlisted_applications': waitlisted_applications,
            'recent_applications': recent_applications,
            'approval_rate': round(approval_rate, 2),
            'rejection_rate': round(rejection_rate, 2),
            'course_wise_applications': course_wise_stats,
            'quota_wise_applications': quota_wise_stats
        }
    })

# Bulk Operations
@admissions_bp.route('/applications/bulk-approve', methods=['POST'])
@handle_errors
def bulk_approve_applications():
    """Bulk approve multiple applications"""
    data = request.get_json()
    application_ids = data.get('application_ids', [])
    reviewed_by = data.get('reviewed_by')
    remarks = data.get('remarks', 'Bulk approved')

    if not application_ids:
        return jsonify({'success': False, 'error': 'No application IDs provided'}), 400

    if not isinstance(application_ids, list):
        return jsonify({'success': False, 'error': 'application_ids must be a list'}), 400

    successful_approvals = []
    failed_approvals = []

    for app_id in application_ids:
        try:
            # Get the application
            app_response = supabase.table('admissions').select('*').eq('id', app_id).execute()
            if not app_response.data:
                failed_approvals.append({'id': app_id, 'error': 'Application not found'})
                continue

            # Update status
            update_data = {
                'status': 'approved',
                'reviewed_by': reviewed_by,
                'remarks': remarks,
                'reviewed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            update_response = supabase.table('admissions').update(update_data).eq('id', app_id).execute()

            if update_response.data:
                # Create student record
                student_result = create_student_from_admission(update_response.data[0])
                if student_result['success']:
                    successful_approvals.append({
                        'id': app_id,
                        'register_number': student_result['register_number']
                    })
                else:
                    failed_approvals.append({
                        'id': app_id,
                        'error': f'Approved but failed to create student: {student_result["error"]}'
                    })
            else:
                failed_approvals.append({'id': app_id, 'error': 'Failed to update application'})

        except Exception as e:
            failed_approvals.append({'id': app_id, 'error': str(e)})

    return jsonify({
        'success': True,
        'message': f'Processed {len(application_ids)} applications',
        'successful_approvals': successful_approvals,
        'failed_approvals': failed_approvals,
        'success_count': len(successful_approvals),
        'failure_count': len(failed_approvals)
    })

@admissions_bp.route('/applications/bulk-reject', methods=['POST'])
@handle_errors
def bulk_reject_applications():
    """Bulk reject multiple applications"""
    data = request.get_json()
    application_ids = data.get('application_ids', [])
    reviewed_by = data.get('reviewed_by')
    remarks = data.get('remarks', 'Bulk rejected')

    if not application_ids:
        return jsonify({'success': False, 'error': 'No application IDs provided'}), 400

    if not isinstance(application_ids, list):
        return jsonify({'success': False, 'error': 'application_ids must be a list'}), 400

    successful_rejections = []
    failed_rejections = []

    for app_id in application_ids:
        try:
            update_data = {
                'status': 'rejected',
                'reviewed_by': reviewed_by,
                'remarks': remarks,
                'reviewed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            update_response = supabase.table('admissions').update(update_data).eq('id', app_id).execute()

            if update_response.data:
                successful_rejections.append(app_id)
            else:
                failed_rejections.append({'id': app_id, 'error': 'Failed to update application'})

        except Exception as e:
            failed_rejections.append({'id': app_id, 'error': str(e)})

    return jsonify({
        'success': True,
        'message': f'Processed {len(application_ids)} applications',
        'successful_rejections': successful_rejections,
        'failed_rejections': failed_rejections,
        'success_count': len(successful_rejections),
        'failure_count': len(failed_rejections)
    })

# Additional utility endpoints
@admissions_bp.route('/applications/pending-count', methods=['GET'])
@handle_errors
def get_pending_applications_count():
    """Get count of pending applications for dashboard"""
    response = supabase.table('admissions').select('id', count='exact').eq('status', 'pending').execute()
    return jsonify({
        'success': True,
        'count': response.count or 0
    })

@admissions_bp.route('/applications/recent', methods=['GET'])
@handle_errors
def get_recent_applications():
    """Get recent applications for dashboard"""
    limit = int(request.args.get('limit', 5))

    response = supabase.table('admissions').select('''
        id,
        application_number,
        full_name,
        email,
        status,
        created_at,
        courses (
            name,
            code
        )
    ''').order('created_at', desc=True).limit(limit).execute()

    return jsonify({
        'success': True,
        'data': response.data
    })

@admissions_bp.route('/upload-document', methods=['POST'])
@handle_errors
def upload_document():
    """Handle document upload for admission applications"""
    # Check if the post request has the file part
    if 'document' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files['document']
    application_id = request.form.get('application_id')
    document_type = request.form.get('document_type', 'other')

    # If user does not select file, browser also submit an empty part without filename
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400

    if not application_id:
        return jsonify({"success": False, "error": "Application ID is required"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # Create uploads directory if it doesn't exist
        upload_folder = os.path.join(os.getcwd(), 'uploads', 'admissions')
        os.makedirs(upload_folder, exist_ok=True)

        # Generate unique filename
        unique_filename = f"{application_id}_{document_type}_{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(upload_folder, unique_filename)

        try:
            # Save the file
            file.save(file_path)

            # Store document information in database (if you have a documents table)
            # For now, we'll just return success with file info

            return jsonify({
                "success": True,
                "message": "Document uploaded successfully",
                "data": {
                    "filename": unique_filename,
                    "original_filename": filename,
                    "document_type": document_type,
                    "application_id": application_id,
                    "upload_date": datetime.now().isoformat()
                }
            })

        except Exception as e:
            return jsonify({"success": False, "error": f"Error saving file: {str(e)}"}), 500

    return jsonify({
        "success": False,
        "error": f"File type not allowed. Allowed types: pdf, doc, docx, txt"
    }), 400
