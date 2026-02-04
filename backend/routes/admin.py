from flask import Blueprint, request, jsonify
from supabase_client import get_supabase
import os
from datetime import datetime, timedelta
import uuid
import random
import string

admin_bp = Blueprint('admin', __name__)

# Initialize Supabase client
supabase = get_supabase()

def generate_user_id():
    """Generate unique user ID in format STU202510001"""
    try:
        current_year = datetime.now().year

        # Get the maximum number for current year
        response = supabase.table('students').select('user_id').like('user_id', f'STU{current_year}%').order('user_id', desc=True).limit(1).execute()

        if response.data and len(response.data) > 0:
            last_user_id = response.data[0]['user_id']
            # Extract the number part (last 5 digits)
            last_number = int(last_user_id[-5:])
            next_number = last_number + 1
        else:
            next_number = 1

        # Generate new user_id
        new_user_id = f'STU{current_year}{str(next_number).zfill(5)}'
        return new_user_id
    except Exception as e:
        # Fallback to random generation if query fails
        return f'STU{datetime.now().year}{str(random.randint(10000, 99999))}'

def generate_random_password(length=8):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for i in range(length))
    return password

@admin_bp.route('/dashboard', methods=['GET'])
def get_dashboard_stats():
    """Get admin dashboard statistics"""
    try:
        # Student statistics
        total_students = supabase.table('students').select('id', count='exact').execute().count

        # Gender statistics
        male_count = 0
        female_count = 0
        try:
            # Get gender counts efficiently with pagination to avoid long-running queries
            limit = 1000
            offset = 0
            while True:
                gender_response = supabase.table('students').select('gender').limit(limit).offset(offset).execute()
                if not gender_response.data:
                    break

                for student in gender_response.data:
                    gender = str(student.get('gender', '')).lower()
                    if 'male' in gender or gender == 'm':
                        male_count += 1
                    elif 'female' in gender or gender == 'f':
                        female_count += 1

                if len(gender_response.data) < limit:
                    break
                offset += limit
        except Exception as e:
            print(f"Warning: Could not fetch gender statistics: {str(e)}")
            male_count = 0
            female_count = 0

        # Faculty statistics
        total_faculty = supabase.table('faculty').select('id', count='exact').execute().count

        # Department statistics
        total_departments = supabase.table('departments').select('id', count='exact').execute().count

        # Admission statistics (handle case where admissions table doesn't exist)
        try:
            total_applications = supabase.table('admissions').select('id', count='exact').execute().count
            pending_applications = supabase.table('admissions').select('id', count='exact').eq('status', 'pending').execute().count
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_admissions = supabase.table('admissions').select('id', count='exact').gte('created_at', week_ago).execute().count
        except Exception as e:
            # If admissions table doesn't exist, set values to 0
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                total_applications = 0
                pending_applications = 0
                recent_admissions = 0
            else:
                raise e

        # Course statistics
        total_courses = supabase.table('courses').select('id', count='exact').execute().count

        # Attendance statistics (last 30 days)
        try:
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            attendance_records = supabase.table('attendance').select('status').gte('created_at', month_ago).execute()

            total_attendance = len(attendance_records.data)
            present_count = len([r for r in attendance_records.data if r['status'] == 'present'])
            overall_attendance = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        except Exception as e:
            print(f"Warning: Could not fetch attendance statistics: {str(e)}")
            total_attendance = 0
            overall_attendance = 0

        return jsonify({
            'success': True,
            'data': {
                'total': total_students,
                'male': male_count,
                'female': female_count,
                'departments': total_departments,
                'faculty': total_faculty,
                'students': {
                    'total': total_students,
                    'new_this_week': recent_admissions
                },
                'faculty_stats': {
                    'total': total_faculty
                },
                'admissions': {
                    'total': total_applications,
                    'pending': pending_applications,
                    'new_this_week': recent_admissions
                },
                'courses': {
                    'total': total_courses
                },
                'attendance': {
                    'overall_percentage': round(overall_attendance, 2),
                    'total_records': total_attendance
                }
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/add_student', methods=['POST'])
def add_student():
    """
    Add new student with all provided details
    """
    try:
        data = request.get_json()
        
        print("Received student data:", data)  # Debug log

        # Validate required fields
        required_fields = ['name', 'roll_no', 'course_id', 'department_id', 'year']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400

        # Get department name from department_id if not provided
        department_name = data.get('department')
        if not department_name and data.get('department_id'):
            dept_response = supabase.table('departments').select('name').eq('id', data['department_id']).execute()
            if dept_response.data and len(dept_response.data) > 0:
                department_name = dept_response.data[0]['name']

        # Get course name from course_id if not provided
        course_name = data.get('course_name')
        if not course_name and data.get('course_id'):
            course_response = supabase.table('courses').select('name').eq('id', data['course_id']).execute()
            if course_response.data and len(course_response.data) > 0:
                course_name = course_response.data[0]['name']

        # Prepare student data with all fields from frontend
        student_data = {
            'name': data['name'],
            'full_name': data.get('full_name', data['name']),
            'roll_no': data['roll_no'],
            'email': data.get('email', f"{data['roll_no'].lower()}@college.edu"),
            'phone': data.get('phone'),
            'gender': data.get('gender', 'male'),
            'date_of_birth': data.get('date_of_birth'),
            'blood_group': data.get('blood_group', 'O+'),
            'address': data.get('address'),
            'register_number': data.get('register_number', f"REG{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            'course_id': data['course_id'],
            'department_id': data['department_id'],
            'year': int(data['year']),
            'current_semester': int(data.get('current_semester', 1)),
            'section': data.get('section', 'A'),
            'admission_year': int(data.get('admission_year', datetime.now().year)),
            'admission_date': data.get('admission_date', datetime.now().date().isoformat()),
            'father_name': data.get('father_name'),
            'mother_name': data.get('mother_name'),
            'guardian_name': data.get('guardian_name'),
            'guardian_phone': data.get('guardian_phone'),
            'annual_income': data.get('annual_income'),
            'status': data.get('status', 'active'),
            'type': data.get('type', 'day_scholar'),
            'quota': data.get('quota', 'GENERAL'),
            'category': data.get('category', 'GENERAL'),
            'quota_type': data.get('quota_type', 'GENERAL'),
            'hostel_required': data.get('hostel_required', False),
            'transport_required': data.get('transport_required', False),
            'first_graduate': data.get('first_graduate', False),
            'created_at': data.get('created_at', datetime.now().isoformat()),
            'updated_at': datetime.now().isoformat(),
            'department': department_name,
            'course_name': course_name
        }
        
        print("Processed student data:", student_data)  # Debug log

        # Insert into students table
        response = supabase.table('students').insert(student_data).execute()
        
        if hasattr(response, 'error') and response.error:
            print("Supabase error:", response.error)  # Debug log
            return jsonify({
                'error': 'Database error',
                'details': str(response.error)
            }), 500

        if not response.data:
            return jsonify({
                'error': 'No data returned from database',
                'details': 'The student might have been created but no data was returned.'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'data': {
                'student': student_data,
                'credentials': {
                    'user_id': data['roll_no'],
                    'email': student_data['email']
                }
            }
        }), 201

    except Exception as e:
        print("Error in add_student:", str(e))  # Debug log
        return jsonify({
            'error': 'Failed to add student',
            'details': str(e)
        }), 500

@admin_bp.route('/students', methods=['GET'])
def get_all_students():
    """Get all students with pagination and filters"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '')
        course_id = request.args.get('course_id')
        year = request.args.get('year')
        type_filter = request.args.get('type')

        # Build query
        query = supabase.table('students').select('*')

        if search:
            query = query.or_(f'name.ilike.%{search}%,user_id.ilike.%{search}%,roll_no.ilike.%{search}%')

        if course_id:
            query = query.eq('course_id', course_id)

        if year:
            query = query.eq('year', year)

        if type_filter:
            query = query.eq('type', type_filter)

        # Execute query with pagination
        offset = (page - 1) * limit
        response = query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()

        # Get total count
        count_query = supabase.table('students').select('id', count='exact')
        if search:
            count_query = count_query.or_(f'name.ilike.%{search}%,user_id.ilike.%{search}%')
        if course_id:
            count_query = count_query.eq('course_id', course_id)
        if year:
            count_query = count_query.eq('year', year)
        if type_filter:
            count_query = count_query.eq('type', type_filter)

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
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_student(student_id):
    """Get, update, or delete a specific student"""
    try:
        if request.method == 'GET':
            response = supabase.table('students').select('*').eq('id', student_id).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'data': response.data[0]
                }), 200
            else:
                return jsonify({'error': 'Student not found'}), 404

        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()

            # Remove fields that shouldn't be updated
            data.pop('user_id', None)
            data.pop('auth_user_id', None)
            data.pop('password', None)
            data.pop('email', None)

            response = supabase.table('students').update(data).eq('id', student_id).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Student updated successfully',
                    'data': response.data[0]
                }), 200
            else:
                return jsonify({'error': 'Student not found'}), 404

        elif request.method == 'DELETE':
            # Get student data first to delete auth user
            student_response = supabase.table('students').select('auth_user_id').eq('id', student_id).execute()

            if student_response.data:
                auth_user_id = student_response.data[0].get('auth_user_id')

                # Delete from students table
                delete_response = supabase.table('students').delete().eq('id', student_id).execute()

                # Delete auth user if exists
                if auth_user_id:
                    try:
                        supabase.auth.admin.delete_user(auth_user_id)
                    except:
                        pass  # Continue even if auth deletion fails

                return jsonify({
                    'success': True,
                    'message': 'Student deleted successfully'
                }), 200
            else:
                return jsonify({'error': 'Student not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/reset_password', methods=['POST'])
def reset_student_password(student_id):
    """Reset student password"""
    try:
        # Generate new password
        new_password = generate_random_password()

        # Get student data
        student_response = supabase.table('students').select('auth_user_id, user_id').eq('id', student_id).execute()

        if not student_response.data:
            return jsonify({'error': 'Student not found'}), 404

        student = student_response.data[0]
        auth_user_id = student.get('auth_user_id')

        # Update password in Supabase Auth
        if auth_user_id:
            try:
                supabase.auth.admin.update_user_by_id(
                    auth_user_id,
                    {"password": new_password}
                )
            except Exception as auth_error:
                return jsonify({'error': f'Failed to reset auth password: {str(auth_error)}'}), 500

        # Update password in students table
        update_response = supabase.table('students').update({
            'password': new_password,
            'updated_at': datetime.now().isoformat()
        }).eq('id', student_id).execute()

        return jsonify({
            'success': True,
            'message': 'Password reset successfully',
            'data': {
                'user_id': student['user_id'],
                'new_password': new_password
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/cleanup_orphaned_auth_users', methods=['POST'])
def cleanup_orphaned_auth_users():
    """
    Cleanup utility to remove auth users that don't have corresponding student records.
    This can happen if student creation fails after auth user is created.
    """
    try:
        # Get all auth users
        auth_users_response = supabase.auth.admin.list_users()

        if not hasattr(auth_users_response, 'users') or not auth_users_response.users:
            return jsonify({
                'success': True,
                'message': 'No auth users found',
                'deleted_count': 0
            }), 200

        # Get all student emails
        students_response = supabase.table('students').select('email, id').execute()
        student_emails = {s['email']: s['id'] for s in students_response.data} if students_response.data else {}

        # Find orphaned auth users (auth users without student records)
        orphaned_users = []
        for auth_user in auth_users_response.users:
            # Check if user has 'student' role in metadata
            user_metadata = auth_user.user_metadata if hasattr(auth_user, 'user_metadata') else {}
            role = user_metadata.get('role', '')

            # Only check student role users
            if role == 'student' and auth_user.email not in student_emails:
                orphaned_users.append({
                    'id': auth_user.id,
                    'email': auth_user.email,
                    'created_at': auth_user.created_at if hasattr(auth_user, 'created_at') else None
                })

        # Delete orphaned users
        deleted_count = 0
        errors = []
        for orphaned_user in orphaned_users:
            try:
                supabase.auth.admin.delete_user(orphaned_user['id'])
                deleted_count += 1
                print(f"Deleted orphaned auth user: {orphaned_user['email']}")
            except Exception as delete_error:
                errors.append({
                    'email': orphaned_user['email'],
                    'error': str(delete_error)
                })
                print(f"Failed to delete orphaned auth user {orphaned_user['email']}: {delete_error}")

        return jsonify({
            'success': True,
            'message': f'Cleanup completed. Deleted {deleted_count} orphaned auth users.',
            'deleted_count': deleted_count,
            'orphaned_users': orphaned_users,
            'errors': errors if errors else None
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Cleanup failed: {str(e)}'
        }), 500

@admin_bp.route('/students/create', methods=['POST'])
def create_student():
    """Create new student record (legacy endpoint)"""
    try:
        data = request.get_json()

        # Generate register number
        year = datetime.now().year
        course_code = data.get('course_code', 'GEN')[:3].upper()
        random_num = str(uuid.uuid4().int)[:4]
        register_number = f"{year}{course_code}{random_num}"

        student_data = {
            'register_number': register_number,
            'course_id': data['course_id'],
            'admission_year': year,
            'current_semester': data.get('current_semester', '1'),
            'shift': data.get('shift', 'day'),
            **{k: v for k, v in data.items() if k not in ['course_code']},
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        response = supabase.table('students').insert(student_data).execute()

        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'data': response.data[0]
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/faculty/create', methods=['POST'])
def create_faculty():
    """Create new faculty record"""
    try:
        data = request.get_json()
        
        # Generate employee ID
        year = datetime.now().year
        dept_code = data.get('department_code', 'GEN')[:3].upper()
        random_num = str(uuid.uuid4().int)[:3]
        employee_id = f"FAC{year}{dept_code}{random_num}"
        
        faculty_data = {
            'employee_id': employee_id,
            'department_id': data['department_id'],
            'designation': data.get('designation'),
            'qualification': data.get('qualification'),
            'experience_years': data.get('experience_years', 0),
            'date_of_joining': data.get('date_of_joining'),
            'specialization': data.get('specialization'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        response = supabase.table('faculty').insert(faculty_data).execute()
        
        return jsonify({
            'success': True,
            'message': 'Faculty created successfully',
            'data': response.data[0]
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses', methods=['GET', 'POST'])
def manage_courses():
    """Get all courses or create new course"""
    try:
        if request.method == 'GET':
            response = supabase.table('courses').select("""
                *,
                departments (
                    name,
                    code
                )
            """).execute()
            
            return jsonify({
                'success': True,
                'data': response.data
            }), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            
            course_data = {
                'name': data['name'],
                'code': data['code'],
                'department_id': data['department_id'],
                'duration_years': data.get('duration_years', 4),
                'total_semesters': data.get('total_semesters', 8),
                'fee_per_semester': data.get('fee_per_semester'),
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('courses').insert(course_data).execute()
            
            return jsonify({
                'success': True,
                'message': 'Course created successfully',
                'data': response.data[0]
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/departments', methods=['GET', 'POST'])
def manage_departments():
    """Get all departments or create new department"""
    try:
        if request.method == 'GET':
            response = supabase.table('departments').select('*').execute()
            
            return jsonify({
                'success': True,
                'data': response.data
            }), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            
            department_data = {
                'name': data['name'],
                'code': data['code'],
                'description': data.get('description'),
                'hod_id': data.get('hod_id'),
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('departments').insert(department_data).execute()
            
            return jsonify({
                'success': True,
                'message': 'Department created successfully',
                'data': response.data[0]
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/attendance/defaulters', methods=['GET'])
def get_attendance_defaulters():
    """Get students with attendance below 75%"""
    try:
        threshold = float(request.args.get('threshold', 75))
        
        # Get all students with their attendance
        students_response = supabase.table('students').select("""
            id,
            register_number,
            profiles (
                full_name,
                email,
                phone
            ),
            courses (
                name,
                code
            )
        """).execute()
        
        defaulters = []
        
        for student in students_response.data:
            # Calculate attendance percentage
            attendance_response = supabase.table('attendance').select('status').eq('student_id', student['id']).execute()
            
            total_classes = len(attendance_response.data)
            if total_classes > 0:
                present_classes = len([r for r in attendance_response.data if r['status'] == 'present'])
                attendance_percentage = (present_classes / total_classes) * 100
                
                if attendance_percentage < threshold:
                    defaulters.append({
                        **student,
                        'attendance_percentage': round(attendance_percentage, 2),
                        'total_classes': total_classes,
                        'present_classes': present_classes,
                        'absent_classes': total_classes - present_classes
                    })
        
        return jsonify({
            'success': True,
            'data': defaulters,
            'threshold': threshold,
            'total_defaulters': len(defaulters)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/academic', methods=['GET'])
def get_academic_report():
    """Get comprehensive academic report"""
    try:
        academic_year = request.args.get('academic_year', '2024-25')
        semester = request.args.get('semester')
        
        # Student performance by course
        courses_response = supabase.table('courses').select("""
            id,
            name,
            code,
            students (
                id,
                current_semester
            )
        """).execute()
        
        course_stats = []
        for course in courses_response.data:
            total_students = len(course['students'])
            
            # Get semester-wise distribution
            semester_distribution = {}
            for student in course['students']:
                sem = student['current_semester']
                semester_distribution[sem] = semester_distribution.get(sem, 0) + 1
            
            course_stats.append({
                'course': course['name'],
                'code': course['code'],
                'total_students': total_students,
                'semester_distribution': semester_distribution
            })
        
        # Overall statistics
        total_students = sum(stat['total_students'] for stat in course_stats)
        
        return jsonify({
            'success': True,
            'data': {
                'academic_year': academic_year,
                'total_students': total_students,
                'course_wise_stats': course_stats,
                'generated_at': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/notifications/broadcast', methods=['POST'])
def broadcast_notification():
    """Send broadcast notification"""
    try:
        data = request.get_json()
        
        notification_data = {
            'title': data['title'],
            'message': data['message'],
            'type': data.get('type', 'general'),
            'target_role': data.get('target_role', 'student'),
            'created_by': data.get('admin_id'),
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('notifications').insert(notification_data).execute()
        
        return jsonify({
            'success': True,
            'message': 'Notification broadcasted successfully',
            'data': response.data[0]
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/hostel/allocations', methods=['GET', 'POST'])
def manage_hostel_allocations():
    """Manage hostel room allocations"""
    try:
        if request.method == 'GET':
            response = supabase.table('hostel_allocations').select("""
                *,
                students (
                    register_number,
                    profiles (
                        full_name
                    )
                ),
                hostel_rooms (
                    room_number,
                    hostels (
                        name,
                        type
                    )
                )
            """).eq('status', 'active').execute()
            
            return jsonify({
                'success': True,
                'data': response.data
            }), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            
            allocation_data = {
                'student_id': data['student_id'],
                'room_id': data['room_id'],
                'allocated_date': data.get('allocated_date', datetime.now().date().isoformat()),
                'status': 'active',
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('hostel_allocations').insert(allocation_data).execute()
            
            # Update room occupancy
            supabase.table('hostel_rooms').update({
                'current_occupancy': supabase.table('hostel_rooms').select('current_occupancy').eq('id', data['room_id']).execute().data[0]['current_occupancy'] + 1
            }).eq('id', data['room_id']).execute()
            
            return jsonify({
                'success': True,
                'message': 'Hostel allocation created successfully',
                'data': response.data[0]
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
