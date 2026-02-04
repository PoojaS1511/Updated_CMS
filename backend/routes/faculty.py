from flask import Blueprint, request, jsonify
from supabase_client import get_supabase
import os
from datetime import datetime, timedelta

faculty_bp = Blueprint('faculty', __name__)

# Initialize Supabase client
supabase = get_supabase()

@faculty_bp.route('/', methods=['GET'])
def get_faculty():
    """Get all faculty members"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')
        department_id = request.args.get('department_id')
        
        query = supabase.table('faculty').select("""
            *,
            profiles (
                full_name,
                email,
                phone
            ),
            departments (
                name,
                code
            )
        """)
        
        if search:
            query = query.or_(f'profiles.full_name.ilike.%{search}%,employee_id.ilike.%{search}%')
        
        if department_id:
            query = query.eq('department_id', department_id)
        
        offset = (page - 1) * limit
        response = query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()
        
        count_response = supabase.table('faculty').select('id', count='exact').execute()
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

@faculty_bp.route('/<faculty_id>/subjects', methods=['GET'])
def get_faculty_subjects(faculty_id):
    """Get subjects assigned to faculty"""
    try:
        academic_year = request.args.get('academic_year', '2024-25')
        semester = request.args.get('semester')
        
        query = supabase.table('subject_assignments').select("""
            *,
            subjects (
                id,
                name,
                code,
                credits,
                courses (
                    name,
                    code
                )
            )
        """).eq('faculty_id', faculty_id).eq('academic_year', academic_year)
        
        if semester:
            query = query.eq('semester', semester)
        
        response = query.execute()
        
        return jsonify({
            'success': True,
            'data': response.data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/<faculty_id>/attendance', methods=['POST'])
def mark_attendance(faculty_id):
    """Mark attendance for students"""
    try:
        data = request.get_json()
        
        attendance_records = []
        for record in data.get('attendance', []):
            attendance_data = {
                'student_id': record['student_id'],
                'subject_assignment_id': record['subject_assignment_id'],
                'date': record['date'],
                'period_number': record.get('period_number', 1),
                'status': record['status'],
                'marked_by': faculty_id,
                'created_at': datetime.now().isoformat()
            }
            attendance_records.append(attendance_data)
        
        if attendance_records:
            response = supabase.table('attendance').insert(attendance_records).execute()
            
            return jsonify({
                'success': True,
                'message': f'Attendance marked for {len(attendance_records)} students',
                'data': response.data
            }), 201
        else:
            return jsonify({'error': 'No attendance records provided'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/<faculty_id>/marks', methods=['POST'])
def enter_marks(faculty_id):
    """Enter marks for students"""
    try:
        data = request.get_json()
        
        marks_records = []
        for record in data.get('marks', []):
            marks_data = {
                'student_id': record['student_id'],
                'subject_id': record['subject_id'],
                'exam_type': record['exam_type'],
                'marks_obtained': record['marks_obtained'],
                'max_marks': record['max_marks'],
                'academic_year': record['academic_year'],
                'semester': record['semester'],
                'remarks': record.get('remarks', ''),
                'entered_by': faculty_id,
                'created_at': datetime.now().isoformat()
            }
            marks_records.append(marks_data)
        
        if marks_records:
            response = supabase.table('marks').insert(marks_records).execute()
            
            return jsonify({
                'success': True,
                'message': f'Marks entered for {len(marks_records)} students',
                'data': response.data
            }), 201
        else:
            return jsonify({'error': 'No marks records provided'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/<faculty_id>/students', methods=['GET'])
def get_faculty_students(faculty_id):
    """Get students taught by faculty"""
    try:
        subject_assignment_id = request.args.get('subject_assignment_id')
        
        if not subject_assignment_id:
            return jsonify({'error': 'Subject assignment ID is required'}), 400
        
        # Get subject assignment details
        assignment_response = supabase.table('subject_assignments').select("""
            *,
            subjects (
                id,
                name,
                code,
                course_id,
                semester
            )
        """).eq('id', subject_assignment_id).eq('faculty_id', faculty_id).execute()
        
        if not assignment_response.data:
            return jsonify({'error': 'Subject assignment not found'}), 404
        
        assignment = assignment_response.data[0]
        
        # Get students for this course and semester
        students_response = supabase.table('students').select("""
            id,
            register_number,
            profiles (
                full_name,
                email
            )
        """).eq('course_id', assignment['subjects']['course_id']).eq('current_semester', assignment['subjects']['semester']).execute()
        
        return jsonify({
            'success': True,
            'data': {
                'subject_assignment': assignment,
                'students': students_response.data
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/<faculty_id>/timetable', methods=['GET'])
def get_faculty_timetable(faculty_id):
    """Get faculty timetable"""
    try:
        response = supabase.table('timetable').select("""
            *,
            subject_assignments (
                subjects (
                    name,
                    code,
                    courses (
                        name,
                        code
                    )
                )
            )
        """).eq('subject_assignments.faculty_id', faculty_id).execute()
        
        # Organize by day
        timetable_by_day = {}
        for entry in response.data:
            day = entry['day_of_week']
            if day not in timetable_by_day:
                timetable_by_day[day] = []
            timetable_by_day[day].append(entry)
        
        # Sort by time
        for day in timetable_by_day:
            timetable_by_day[day].sort(key=lambda x: x['start_time'])
        
        return jsonify({
            'success': True,
            'data': timetable_by_day
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/<faculty_id>/notifications', methods=['POST'])
def send_notification(faculty_id):
    """Send notification to students"""
    try:
        data = request.get_json()
        
        notification_data = {
            'title': data['title'],
            'message': data['message'],
            'type': data.get('type', 'general'),
            'target_role': 'student',
            'created_by': faculty_id,
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('notifications').insert(notification_data).execute()
        
        return jsonify({
            'success': True,
            'message': 'Notification sent successfully',
            'data': response.data[0]
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/<faculty_id>/performance-report', methods=['GET'])
def get_performance_report(faculty_id):
    """Get faculty performance report"""
    try:
        # Get subjects taught
        subjects_response = supabase.table('subject_assignments').select("""
            subjects (
                name,
                code
            )
        """).eq('faculty_id', faculty_id).execute()
        
        # Get attendance marking statistics
        attendance_response = supabase.table('attendance').select('id', count='exact').eq('marked_by', faculty_id).execute()
        
        # Get marks entry statistics
        marks_response = supabase.table('marks').select('id', count='exact').eq('entered_by', faculty_id).execute()
        
        return jsonify({
            'success': True,
            'data': {
                'subjects_taught': len(subjects_response.data),
                'attendance_sessions_conducted': attendance_response.count,
                'marks_entries': marks_response.count,
                'subjects': subjects_response.data
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
