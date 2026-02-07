from flask import Blueprint, request, jsonify
from supabase_client import get_supabase
from datetime import datetime, timedelta
from functools import wraps

attendance_bp = Blueprint('attendance', __name__)

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

# Attendance Management
@attendance_bp.route('/attendance', methods=['GET'])
@handle_errors
def get_attendance():
    """Get attendance records with optional filtering"""
    query = supabase.table('attendance').select('''
        *,
        students (
            id,
            register_number,
            full_name,
            courses (
                name,
                code
            )
        ),
        subjects (
            id,
            name,
            code
        ),
        faculty (
            id,
            full_name,
            employee_id
        )
    ''')
    
    # Add filters if provided
    if request.args.get('student_id'):
        query = query.eq('student_id', request.args.get('student_id'))
    if request.args.get('subject_id'):
        query = query.eq('subject_id', request.args.get('subject_id'))
    if request.args.get('faculty_id'):
        query = query.eq('faculty_id', request.args.get('faculty_id'))
    if request.args.get('date'):
        query = query.eq('date', request.args.get('date'))
    if request.args.get('status'):
        query = query.eq('status', request.args.get('status'))
    if request.args.get('date_from') and request.args.get('date_to'):
        query = query.gte('date', request.args.get('date_from')).lte('date', request.args.get('date_to'))
    
    result = query.order('date', desc=True).execute()
    return jsonify({"success": True, "data": result.data})

@attendance_bp.route('/attendance', methods=['POST'])
@handle_errors
def mark_attendance():
    """Mark attendance for students"""
    data = request.get_json()
    
    # Support both single attendance and bulk attendance marking
    if 'attendance_records' in data:
        # Bulk attendance marking
        attendance_records = data['attendance_records']
        required_fields = ['student_id', 'subject_id', 'faculty_id', 'date', 'status']
        
        for record in attendance_records:
            for field in required_fields:
                if field not in record:
                    return jsonify({"success": False, "error": f"Missing required field: {field} in attendance record"}), 400
        
        # Validate all records first
        for record in attendance_records:
            # Check if student exists
            student_result = supabase.table('students').select('id').eq('id', record['student_id']).execute()
            if not student_result.data:
                return jsonify({"success": False, "error": f"Invalid student_id: {record['student_id']}"}), 400
            
            # Check if subject exists
            subject_result = supabase.table('subjects').select('id').eq('id', record['subject_id']).execute()
            if not subject_result.data:
                return jsonify({"success": False, "error": f"Invalid subject_id: {record['subject_id']}"}), 400
            
            # Check if faculty exists
            faculty_result = supabase.table('faculty').select('id').eq('id', record['faculty_id']).execute()
            if not faculty_result.data:
                return jsonify({"success": False, "error": f"Invalid faculty_id: {record['faculty_id']}"}), 400
            
            # Validate status
            valid_statuses = ['present', 'absent', 'late']
            if record['status'] not in valid_statuses:
                return jsonify({"success": False, "error": f"Invalid status: {record['status']}. Must be one of: {valid_statuses}"}), 400
        
        # Check for existing attendance records
        for record in attendance_records:
            existing = supabase.table('attendance').select('id').eq('student_id', record['student_id']).eq('subject_id', record['subject_id']).eq('date', record['date']).execute()
            if existing.data:
                return jsonify({"success": False, "error": f"Attendance already marked for student {record['student_id']} on {record['date']}"}), 400
        
        # Insert all records
        for record in attendance_records:
            attendance_data = {
                'student_id': record['student_id'],
                'subject_id': record['subject_id'],
                'faculty_id': record['faculty_id'],
                'date': record['date'],
                'status': record['status'],
                'remarks': record.get('remarks'),
                'created_at': datetime.now().isoformat()
            }
            supabase.table('attendance').insert(attendance_data).execute()
        
        return jsonify({"success": True, "message": f"Attendance marked for {len(attendance_records)} students"}), 201
    
    else:
        # Single attendance marking
        required_fields = ['student_id', 'subject_id', 'faculty_id', 'date', 'status']
        
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        # Validate entities exist
        student_result = supabase.table('students').select('id').eq('id', data['student_id']).execute()
        if not student_result.data:
            return jsonify({"success": False, "error": "Invalid student_id"}), 400
        
        subject_result = supabase.table('subjects').select('id').eq('id', data['subject_id']).execute()
        if not subject_result.data:
            return jsonify({"success": False, "error": "Invalid subject_id"}), 400
        
        faculty_result = supabase.table('faculty').select('id').eq('id', data['faculty_id']).execute()
        if not faculty_result.data:
            return jsonify({"success": False, "error": "Invalid faculty_id"}), 400
        
        # Validate status
        valid_statuses = ['present', 'absent', 'late']
        if data['status'] not in valid_statuses:
            return jsonify({"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}), 400
        
        # Check if attendance already exists
        existing = supabase.table('attendance').select('id').eq('student_id', data['student_id']).eq('subject_id', data['subject_id']).eq('date', data['date']).execute()
        if existing.data:
            return jsonify({"success": False, "error": "Attendance already marked for this student on this date"}), 400
        
        attendance_data = {
            'student_id': data['student_id'],
            'subject_id': data['subject_id'],
            'faculty_id': data['faculty_id'],
            'date': data['date'],
            'status': data['status'],
            'remarks': data.get('remarks'),
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('attendance').insert(attendance_data).execute()
        return jsonify({"success": True, "data": result.data[0] if result.data else {}}), 201

@attendance_bp.route('/attendance/<int:attendance_id>', methods=['PUT'])
@handle_errors
def update_attendance(attendance_id):
    """Update attendance record"""
    data = request.get_json()
    
    # Validate status if provided
    if 'status' in data:
        valid_statuses = ['present', 'absent', 'late']
        if data['status'] not in valid_statuses:
            return jsonify({"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}), 400
    
    result = supabase.table('attendance').update(data).eq('id', attendance_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Attendance record not found"}), 404
    
    return jsonify({"success": True, "data": result.data[0]})

@attendance_bp.route('/attendance/<int:attendance_id>', methods=['DELETE'])
@handle_errors
def delete_attendance(attendance_id):
    """Delete attendance record"""
    result = supabase.table('attendance').delete().eq('id', attendance_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Attendance record not found"}), 404
    
    return jsonify({"success": True, "message": "Attendance record deleted successfully"})

# Attendance Analytics
@attendance_bp.route('/attendance/analytics/student/<int:student_id>', methods=['GET'])
@handle_errors
def get_student_attendance_analytics(student_id):
    """Get attendance analytics for a specific student"""
    # Get all attendance records for the student
    result = supabase.table('attendance').select('''
        *,
        subjects (
            name,
            code
        )
    ''').eq('student_id', student_id).execute()
    
    if not result.data:
        return jsonify({"success": False, "error": "No attendance records found for this student"}), 404
    
    attendance_data = result.data
    total_classes = len(attendance_data)
    
    # Calculate overall statistics
    present_count = len([record for record in attendance_data if record['status'] == 'present'])
    absent_count = len([record for record in attendance_data if record['status'] == 'absent'])
    late_count = len([record for record in attendance_data if record['status'] == 'late'])
    
    overall_percentage = (present_count / total_classes) * 100 if total_classes > 0 else 0
    
    # Subject-wise analytics
    subject_analytics = {}
    for record in attendance_data:
        subject_name = record['subjects']['name']
        if subject_name not in subject_analytics:
            subject_analytics[subject_name] = {
                'subject_code': record['subjects']['code'],
                'total_classes': 0,
                'present': 0,
                'absent': 0,
                'late': 0
            }
        
        subject_analytics[subject_name]['total_classes'] += 1
        subject_analytics[subject_name][record['status']] += 1
    
    # Calculate percentage for each subject
    for subject in subject_analytics:
        total = subject_analytics[subject]['total_classes']
        present = subject_analytics[subject]['present']
        subject_analytics[subject]['percentage'] = (present / total) * 100 if total > 0 else 0
    
    analytics = {
        'student_id': student_id,
        'overall_statistics': {
            'total_classes': total_classes,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'attendance_percentage': round(overall_percentage, 2)
        },
        'subject_wise_analytics': subject_analytics
    }
    
    return jsonify({"success": True, "data": analytics})

@attendance_bp.route('/attendance/analytics/subject/<int:subject_id>', methods=['GET'])
@handle_errors
def get_subject_attendance_analytics(subject_id):
    """Get attendance analytics for a specific subject"""
    # Get all attendance records for the subject
    result = supabase.table('attendance').select('''
        *,
        students (
            register_number,
            full_name
        )
    ''').eq('subject_id', subject_id).execute()

    if not result.data:
        return jsonify({"success": False, "error": "No attendance records found for this subject"}), 404

    attendance_data = result.data
    total_records = len(attendance_data)

    # Calculate overall statistics
    present_count = len([record for record in attendance_data if record['status'] == 'present'])
    absent_count = len([record for record in attendance_data if record['status'] == 'absent'])
    late_count = len([record for record in attendance_data if record['status'] == 'late'])

    overall_percentage = (present_count / total_records) * 100 if total_records > 0 else 0

    # Student-wise analytics
    student_analytics = {}
    for record in attendance_data:
        student_id = record['student_id']
        if student_id not in student_analytics:
            student_analytics[student_id] = {
                'student_name': record['students']['full_name'],
                'register_number': record['students']['register_number'],
                'total_classes': 0,
                'present': 0,
                'absent': 0,
                'late': 0
            }

        student_analytics[student_id]['total_classes'] += 1
        student_analytics[student_id][record['status']] += 1

    # Calculate percentage for each student and identify defaulters
    defaulters = []
    for student_id, data in student_analytics.items():
        total = data['total_classes']
        present = data['present']
        percentage = (present / total) * 100 if total > 0 else 0
        data['percentage'] = round(percentage, 2)

        # Consider students with less than 75% attendance as defaulters
        if percentage < 75:
            defaulters.append({
                'student_id': student_id,
                'student_name': data['student_name'],
                'register_number': data['register_number'],
                'attendance_percentage': percentage,
                'absent_classes': data['absent']
            })

    analytics = {
        'subject_id': subject_id,
        'overall_statistics': {
            'total_records': total_records,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'overall_percentage': round(overall_percentage, 2)
        },
        'student_wise_analytics': student_analytics,
        'defaulters': defaulters,
        'defaulters_count': len(defaulters)
    }

    return jsonify({"success": True, "data": analytics})

@attendance_bp.route('/attendance/analytics/faculty/<int:faculty_id>', methods=['GET'])
@handle_errors
def get_faculty_attendance_analytics(faculty_id):
    """Get attendance analytics for classes taken by a specific faculty"""
    # Get all attendance records for the faculty
    result = supabase.table('attendance').select('''
        *,
        subjects (
            name,
            code
        ),
        students (
            register_number,
            full_name
        )
    ''').eq('faculty_id', faculty_id).execute()

    if not result.data:
        return jsonify({"success": False, "error": "No attendance records found for this faculty"}), 404

    attendance_data = result.data
    total_records = len(attendance_data)

    # Calculate overall statistics
    present_count = len([record for record in attendance_data if record['status'] == 'present'])
    absent_count = len([record for record in attendance_data if record['status'] == 'absent'])
    late_count = len([record for record in attendance_data if record['status'] == 'late'])

    overall_percentage = (present_count / total_records) * 100 if total_records > 0 else 0

    # Subject-wise analytics
    subject_analytics = {}
    for record in attendance_data:
        subject_name = record['subjects']['name']
        if subject_name not in subject_analytics:
            subject_analytics[subject_name] = {
                'subject_code': record['subjects']['code'],
                'total_classes': 0,
                'present': 0,
                'absent': 0,
                'late': 0
            }

        subject_analytics[subject_name]['total_classes'] += 1
        subject_analytics[subject_name][record['status']] += 1

    # Calculate percentage for each subject
    for subject in subject_analytics:
        total = subject_analytics[subject]['total_classes']
        present = subject_analytics[subject]['present']
        subject_analytics[subject]['percentage'] = round((present / total) * 100, 2) if total > 0 else 0

    analytics = {
        'faculty_id': faculty_id,
        'overall_statistics': {
            'total_records': total_records,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'overall_percentage': round(overall_percentage, 2)
        },
        'subject_wise_analytics': subject_analytics
    }

    return jsonify({"success": True, "data": analytics})

@attendance_bp.route('/attendance/defaulters', methods=['GET'])
@handle_errors
def get_attendance_defaulters():
    """Get list of students with low attendance across all subjects"""
    # Get all attendance records
    result = supabase.table('attendance').select('''
        *,
        students (
            register_number,
            full_name,
            courses (
                name,
                code
            )
        ),
        subjects (
            name,
            code
        )
    ''').execute()

    if not result.data:
        return jsonify({"success": True, "data": []}), 200

    attendance_data = result.data

    # Calculate student-wise attendance
    student_analytics = {}
    for record in attendance_data:
        student_id = record['student_id']
        if student_id not in student_analytics:
            student_analytics[student_id] = {
                'student_name': record['students']['full_name'],
                'register_number': record['students']['register_number'],
                'course': record['students']['courses']['name'] if record['students']['courses'] else 'N/A',
                'total_classes': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'subjects': set()
            }

        student_analytics[student_id]['total_classes'] += 1
        student_analytics[student_id][record['status']] += 1
        student_analytics[student_id]['subjects'].add(record['subjects']['name'])

    # Identify defaulters (students with less than 75% attendance)
    defaulters = []
    threshold = float(request.args.get('threshold', 75))  # Default threshold is 75%

    for student_id, data in student_analytics.items():
        total = data['total_classes']
        present = data['present']
        percentage = (present / total) * 100 if total > 0 else 0

        if percentage < threshold:
            defaulters.append({
                'student_id': student_id,
                'student_name': data['student_name'],
                'register_number': data['register_number'],
                'course': data['course'],
                'total_classes': total,
                'present_classes': present,
                'absent_classes': data['absent'],
                'late_classes': data['late'],
                'attendance_percentage': round(percentage, 2),
                'subjects_count': len(data['subjects'])
            })

    # Sort by attendance percentage (lowest first)
    defaulters.sort(key=lambda x: x['attendance_percentage'])

    return jsonify({
        "success": True,
        "data": defaulters,
        "count": len(defaulters),
        "threshold": threshold
    })
