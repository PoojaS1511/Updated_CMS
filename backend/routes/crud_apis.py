from flask import Blueprint, request, jsonify
from supabase_client import get_supabase
from datetime import datetime

crud_bp = Blueprint('crud', __name__)

# Initialize Supabase client
supabase = get_supabase()

# =====================================================
# COURSES CRUD
# =====================================================
@crud_bp.route('/courses', methods=['GET', 'POST'])
def manage_courses():
    """Get all courses or create new course"""
    try:
        if request.method == 'GET':
            response = supabase.table('courses').select('*').execute()
            return jsonify({'success': True, 'data': response.data}), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            response = supabase.table('courses').insert(data).execute()
            return jsonify({'success': True, 'message': 'Course created', 'data': response.data[0]}), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/courses/<int:course_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_course(course_id):
    """Get, update, or delete a specific course"""
    try:
        if request.method == 'GET':
            response = supabase.table('courses').select('*').eq('id', course_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Course not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('courses').update(data).eq('id', course_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Course updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Course not found'}), 404
        
        elif request.method == 'DELETE':
            response = supabase.table('courses').delete().eq('id', course_id).execute()
            return jsonify({'success': True, 'message': 'Course deleted'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# SUBJECTS CRUD
# =====================================================
@crud_bp.route('/subjects', methods=['GET', 'POST'])
def manage_subjects():
    """Get all subjects or create new subject"""
    try:
        if request.method == 'GET':
            course_id = request.args.get('course_id')
            query = supabase.table('subjects').select('*')
            if course_id:
                query = query.eq('course_id', course_id)
            response = query.execute()
            return jsonify({'success': True, 'data': response.data}), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            response = supabase.table('subjects').insert(data).execute()
            return jsonify({'success': True, 'message': 'Subject created', 'data': response.data[0]}), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/subjects/<int:subject_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_subject(subject_id):
    """Get, update, or delete a specific subject"""
    try:
        if request.method == 'GET':
            response = supabase.table('subjects').select('*').eq('id', subject_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Subject not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('subjects').update(data).eq('id', subject_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Subject updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Subject not found'}), 404
        
        elif request.method == 'DELETE':
            response = supabase.table('subjects').delete().eq('id', subject_id).execute()
            return jsonify({'success': True, 'message': 'Subject deleted'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# EXAMS CRUD
# =====================================================
@crud_bp.route('/exams', methods=['GET', 'POST'])
def manage_exams():
    """Get all exams or create new exam"""
    try:
        if request.method == 'GET':
            course_id = request.args.get('course_id')
            query = supabase.table('exams').select('*')
            if course_id:
                query = query.eq('course_id', course_id)
            response = query.execute()
            return jsonify({'success': True, 'data': response.data}), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            response = supabase.table('exams').insert(data).execute()
            return jsonify({'success': True, 'message': 'Exam created', 'data': response.data[0]}), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/exams/<int:exam_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_exam(exam_id):
    """Get, update, or delete a specific exam"""
    try:
        if request.method == 'GET':
            response = supabase.table('exams').select('*').eq('id', exam_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Exam not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('exams').update(data).eq('id', exam_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Exam updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Exam not found'}), 404
        
        elif request.method == 'DELETE':
            response = supabase.table('exams').delete().eq('id', exam_id).execute()
            return jsonify({'success': True, 'message': 'Exam deleted'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# NOTIFICATIONS CRUD
# =====================================================
@crud_bp.route('/notifications', methods=['GET', 'POST'])
def manage_notifications():
    """Get all notifications or create new notification"""
    try:
        if request.method == 'GET':
            notification_type = request.args.get('type')
            query = supabase.table('notifications').select('*')
            if notification_type:
                query = query.eq('notification_type', notification_type)
            response = query.order('created_at', desc=True).execute()
            return jsonify({'success': True, 'data': response.data}), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            
            response = supabase.table('notifications').insert(data).execute()
            return jsonify({'success': True, 'message': 'Notification created', 'data': response.data[0]}), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/notifications/<int:notification_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_notification(notification_id):
    """Get, update, or delete a specific notification"""
    try:
        if request.method == 'GET':
            response = supabase.table('notifications').select('*').eq('id', notification_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Notification not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            response = supabase.table('notifications').update(data).eq('id', notification_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Notification updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Notification not found'}), 404
        
        elif request.method == 'DELETE':
            response = supabase.table('notifications').delete().eq('id', notification_id).execute()
            return jsonify({'success': True, 'message': 'Notification deleted'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# EVENTS CRUD
# =====================================================
@crud_bp.route('/events', methods=['GET', 'POST'])
def manage_events():
    """Get all events or create new event"""
    try:
        if request.method == 'GET':
            event_type = request.args.get('type')
            query = supabase.table('events').select('*')
            if event_type:
                query = query.eq('event_type', event_type)
            response = query.order('event_date').execute()
            return jsonify({'success': True, 'data': response.data}), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            response = supabase.table('events').insert(data).execute()
            return jsonify({'success': True, 'message': 'Event created', 'data': response.data[0]}), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/events/<int:event_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_event(event_id):
    """Get, update, or delete a specific event"""
    try:
        if request.method == 'GET':
            response = supabase.table('events').select('*').eq('id', event_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Event not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('events').update(data).eq('id', event_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Event updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Event not found'}), 404
        
        elif request.method == 'DELETE':
            response = supabase.table('events').delete().eq('id', event_id).execute()
            return jsonify({'success': True, 'message': 'Event deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# TIMETABLE CRUD
# =====================================================
@crud_bp.route('/timetable', methods=['GET', 'POST'])
def manage_timetable():
    """Get all timetable entries or create new entry"""
    try:
        if request.method == 'GET':
            course_id = request.args.get('course_id')
            year = request.args.get('year')
            query = supabase.table('timetable').select('*')
            if course_id:
                query = query.eq('course_id', course_id)
            if year:
                query = query.eq('year', year)
            response = query.execute()
            return jsonify({'success': True, 'data': response.data}), 200

        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()

            response = supabase.table('timetable').insert(data).execute()
            return jsonify({'success': True, 'message': 'Timetable entry created', 'data': response.data[0]}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/timetable/<int:timetable_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_timetable_entry(timetable_id):
    """Get, update, or delete a specific timetable entry"""
    try:
        if request.method == 'GET':
            response = supabase.table('timetable').select('*').eq('id', timetable_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Timetable entry not found'}), 404

        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('timetable').update(data).eq('id', timetable_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Timetable updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Timetable entry not found'}), 404

        elif request.method == 'DELETE':
            response = supabase.table('timetable').delete().eq('id', timetable_id).execute()
            return jsonify({'success': True, 'message': 'Timetable entry deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# TRANSPORT CRUD
# =====================================================
@crud_bp.route('/transport', methods=['GET', 'POST'])
def manage_transport():
    """Get all transport routes or create new route"""
    try:
        if request.method == 'GET':
            response = supabase.table('transport').select('*').execute()
            return jsonify({'success': True, 'data': response.data}), 200

        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()

            response = supabase.table('transport').insert(data).execute()
            return jsonify({'success': True, 'message': 'Transport route created', 'data': response.data[0]}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/transport/<int:transport_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_transport_route(transport_id):
    """Get, update, or delete a specific transport route"""
    try:
        if request.method == 'GET':
            response = supabase.table('transport').select('*').eq('id', transport_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Transport route not found'}), 404

        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('transport').update(data).eq('id', transport_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Transport route updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Transport route not found'}), 404

        elif request.method == 'DELETE':
            response = supabase.table('transport').delete().eq('id', transport_id).execute()
            return jsonify({'success': True, 'message': 'Transport route deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# HOSTELS CRUD
# =====================================================
@crud_bp.route('/hostels', methods=['GET', 'POST'])
def manage_hostels():
    """Get all hostels or create new hostel"""
    try:
        if request.method == 'GET':
            response = supabase.table('hostels').select('*').execute()
            return jsonify({'success': True, 'data': response.data}), 200

        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()

            response = supabase.table('hostels').insert(data).execute()
            return jsonify({'success': True, 'message': 'Hostel created', 'data': response.data[0]}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/hostels/<int:hostel_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_hostel(hostel_id):
    """Get, update, or delete a specific hostel"""
    try:
        if request.method == 'GET':
            response = supabase.table('hostels').select('*').eq('id', hostel_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Hostel not found'}), 404

        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('hostels').update(data).eq('id', hostel_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Hostel updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Hostel not found'}), 404

        elif request.method == 'DELETE':
            response = supabase.table('hostels').delete().eq('id', hostel_id).execute()
            return jsonify({'success': True, 'message': 'Hostel deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# INTERNSHIPS CRUD
# =====================================================
@crud_bp.route('/internships', methods=['GET', 'POST'])
def manage_internships():
    """Get all internships or create new internship"""
    try:
        if request.method == 'GET':
            student_id = request.args.get('student_id')
            query = supabase.table('internships').select('*')
            if student_id:
                query = query.eq('student_id', student_id)
            response = query.execute()
            return jsonify({'success': True, 'data': response.data}), 200

        elif request.method == 'POST':
            data = request.get_json()
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()

            response = supabase.table('internships').insert(data).execute()
            return jsonify({'success': True, 'message': 'Internship created', 'data': response.data[0]}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crud_bp.route('/internships/<int:internship_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_internship(internship_id):
    """Get, update, or delete a specific internship"""
    try:
        if request.method == 'GET':
            response = supabase.table('internships').select('*').eq('id', internship_id).execute()
            if response.data:
                return jsonify({'success': True, 'data': response.data[0]}), 200
            return jsonify({'error': 'Internship not found'}), 404

        elif request.method == 'PUT':
            data = request.get_json()
            data['updated_at'] = datetime.now().isoformat()
            response = supabase.table('internships').update(data).eq('id', internship_id).execute()
            if response.data:
                return jsonify({'success': True, 'message': 'Internship updated', 'data': response.data[0]}), 200
            return jsonify({'error': 'Internship not found'}), 404

        elif request.method == 'DELETE':
            response = supabase.table('internships').delete().eq('id', internship_id).execute()
            return jsonify({'success': True, 'message': 'Internship deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

