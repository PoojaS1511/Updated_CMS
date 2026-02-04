from flask import Blueprint, request, jsonify
from supabase_client import get_supabase
from datetime import datetime, timedelta
from functools import wraps
import uuid

notifications_bp = Blueprint('notifications', __name__)

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

# Communication Center - Notification Management
@notifications_bp.route('/notifications', methods=['GET'])
@handle_errors
def get_notifications():
    """Get all notifications with optional filtering"""
    query = supabase.table('notifications').select('*')

    # Add filters if provided
    if request.args.get('notification_type'):
        query = query.eq('notification_type', request.args.get('notification_type'))
    if request.args.get('target_audience'):
        query = query.eq('target_audience', request.args.get('target_audience'))
    if request.args.get('target_course_id'):
        query = query.eq('target_course_id', request.args.get('target_course_id'))
    if request.args.get('target_semester'):
        query = query.eq('target_semester', request.args.get('target_semester'))
    if request.args.get('is_active'):
        query = query.eq('is_active', request.args.get('is_active').lower() == 'true')
    if request.args.get('search'):
        search_term = request.args.get('search')
        query = query.or_(f'title.ilike.%{search_term}%,message.ilike.%{search_term}%')

    result = query.order('created_at', desc=True).execute()
    return jsonify({"success": True, "data": result.data})

@notifications_bp.route('/notifications', methods=['POST'])
@handle_errors
def create_notification():
    """Create and send a new notification"""
    data = request.get_json()
    required_fields = ['title', 'message', 'target_audience']

    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    # Validate notification_type
    valid_notification_types = ['general', 'academic', 'administrative', 'events', 'urgent']
    notification_type = data.get('notification_type', 'general')
    if notification_type not in valid_notification_types:
        return jsonify({"success": False, "error": f"Invalid notification_type. Must be one of: {valid_notification_types}"}), 400

    # Validate target_audience
    valid_target_audiences = ['all', 'students', 'faculty', 'specific']
    if data['target_audience'] not in valid_target_audiences:
        return jsonify({"success": False, "error": f"Invalid target_audience. Must be one of: {valid_target_audiences}"}), 400

    # If target_audience is 'specific', validate target_course_id
    if data['target_audience'] == 'specific' and 'target_course_id' in data:
        course_result = supabase.table('courses').select('id').eq('id', data['target_course_id']).execute()
        if not course_result.data:
            return jsonify({"success": False, "error": "Invalid target_course_id"}), 400

    notification_data = {
        'title': data['title'],
        'message': data['message'],
        'notification_type': notification_type,
        'target_audience': data['target_audience'],
        'target_course_id': data.get('target_course_id'),
        'target_semester': data.get('target_semester'),
        'sender_id': data.get('sender_id'),  # In real app, this would come from auth
        'is_active': data.get('is_active', True),
        'expires_at': data.get('expires_at'),
        'created_at': datetime.now().isoformat()
    }

    result = supabase.table('notifications').insert(notification_data).execute()

    if result.data:
        # In a real application, you would trigger actual notification sending here
        # For now, we'll just return success
        return jsonify({
            "success": True,
            "message": "Notification created and sent successfully",
            "data": result.data[0]
        }), 201
    else:
        return jsonify({"success": False, "error": "Failed to create notification"}), 500

@notifications_bp.route('/notifications/<int:notification_id>', methods=['GET'])
@handle_errors
def get_notification(notification_id):
    """Get a specific notification by ID"""
    result = supabase.table('notifications').select('*').eq('id', notification_id).execute()

    if not result.data:
        return jsonify({"success": False, "error": "Notification not found"}), 404

    return jsonify({"success": True, "data": result.data[0]})

@notifications_bp.route('/notifications/<int:notification_id>', methods=['PUT'])
@handle_errors
def update_notification(notification_id):
    """Update a notification"""
    data = request.get_json()

    # Validate notification_type if provided
    if 'notification_type' in data:
        valid_notification_types = ['general', 'academic', 'administrative', 'events', 'urgent']
        if data['notification_type'] not in valid_notification_types:
            return jsonify({"success": False, "error": f"Invalid notification_type. Must be one of: {valid_notification_types}"}), 400

    # Validate target_audience if provided
    if 'target_audience' in data:
        valid_target_audiences = ['all', 'students', 'faculty', 'specific']
        if data['target_audience'] not in valid_target_audiences:
            return jsonify({"success": False, "error": f"Invalid target_audience. Must be one of: {valid_target_audiences}"}), 400

    # Validate target_course_id if provided
    if 'target_course_id' in data and data['target_course_id']:
        course_result = supabase.table('courses').select('id').eq('id', data['target_course_id']).execute()
        if not course_result.data:
            return jsonify({"success": False, "error": "Invalid target_course_id"}), 400

    result = supabase.table('notifications').update(data).eq('id', notification_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Notification not found"}), 404

    return jsonify({"success": True, "data": result.data[0]})

@notifications_bp.route('/notifications/<int:notification_id>', methods=['DELETE'])
@handle_errors
def delete_notification(notification_id):
    """Delete a notification"""
    result = supabase.table('notifications').delete().eq('id', notification_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Notification not found"}), 404

    return jsonify({"success": True, "message": "Notification deleted successfully"})

@notifications_bp.route('/notifications/<int:notification_id>/toggle', methods=['PATCH'])
@handle_errors
def toggle_notification_status(notification_id):
    """Toggle notification active status"""
    data = request.get_json()

    if 'is_active' not in data:
        return jsonify({"success": False, "error": "Missing is_active field"}), 400

    result = supabase.table('notifications').update({
        'is_active': data['is_active']
    }).eq('id', notification_id).execute()

    if not result.data:
        return jsonify({"success": False, "error": "Notification not found"}), 404

    status = "activated" if data['is_active'] else "deactivated"
    return jsonify({"success": True, "message": f"Notification {status} successfully", "data": result.data[0]})

# Targeted Notification Endpoints
@notifications_bp.route('/notifications/send-to-course', methods=['POST'])
@handle_errors
def send_notification_to_course():
    """Send notification to all students in a specific course"""
    data = request.get_json()
    required_fields = ['title', 'message', 'course_id']

    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    # Validate course exists
    course_result = supabase.table('courses').select('id, name').eq('id', data['course_id']).execute()
    if not course_result.data:
        return jsonify({"success": False, "error": "Invalid course_id"}), 400

    # Create notification
    notification_data = {
        'title': data['title'],
        'message': data['message'],
        'notification_type': data.get('notification_type', 'academic'),
        'target_audience': 'specific',
        'target_course_id': data['course_id'],
        'target_semester': data.get('semester'),
        'sender_id': data.get('sender_id'),
        'is_active': True,
        'created_at': datetime.now().isoformat()
    }

    result = supabase.table('notifications').insert(notification_data).execute()

    if result.data:
        # Get count of students who will receive this notification
        students_query = supabase.table('students').select('id', count='exact').eq('course_id', data['course_id'])
        if data.get('semester'):
            students_query = students_query.eq('current_semester', data['semester'])

        students_count = students_query.execute().count or 0

        return jsonify({
            "success": True,
            "message": f"Notification sent to {students_count} students in {course_result.data[0]['name']}",
            "data": result.data[0],
            "recipients_count": students_count
        }), 201
    else:
        return jsonify({"success": False, "error": "Failed to send notification"}), 500

@notifications_bp.route('/notifications/send-to-faculty', methods=['POST'])
@handle_errors
def send_notification_to_faculty():
    """Send notification to all faculty members"""
    data = request.get_json()
    required_fields = ['title', 'message']

    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    # Create notification
    notification_data = {
        'title': data['title'],
        'message': data['message'],
        'notification_type': data.get('notification_type', 'administrative'),
        'target_audience': 'faculty',
        'sender_id': data.get('sender_id'),
        'is_active': True,
        'created_at': datetime.now().isoformat()
    }

    result = supabase.table('notifications').insert(notification_data).execute()

    if result.data:
        # Get count of faculty members
        faculty_count = supabase.table('faculty').select('id', count='exact').execute().count or 0

        return jsonify({
            "success": True,
            "message": f"Notification sent to {faculty_count} faculty members",
            "data": result.data[0],
            "recipients_count": faculty_count
        }), 201
    else:
        return jsonify({"success": False, "error": "Failed to send notification"}), 500

@notifications_bp.route('/notifications/send-to-all', methods=['POST'])
@handle_errors
def send_notification_to_all():
    """Send notification to all users (students and faculty)"""
    data = request.get_json()
    required_fields = ['title', 'message']

    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    # Create notification
    notification_data = {
        'title': data['title'],
        'message': data['message'],
        'notification_type': data.get('notification_type', 'general'),
        'target_audience': 'all',
        'sender_id': data.get('sender_id'),
        'is_active': True,
        'created_at': datetime.now().isoformat()
    }

    result = supabase.table('notifications').insert(notification_data).execute()

    if result.data:
        # Get count of all users
        students_count = supabase.table('students').select('id', count='exact').execute().count or 0
        faculty_count = supabase.table('faculty').select('id', count='exact').execute().count or 0
        total_recipients = students_count + faculty_count

        return jsonify({
            "success": True,
            "message": f"Notification sent to all users ({students_count} students, {faculty_count} faculty)",
            "data": result.data[0],
            "recipients_count": total_recipients
        }), 201
    else:
        return jsonify({"success": False, "error": "Failed to send notification"}), 500

# User-specific notification endpoints
@notifications_bp.route('/notifications/student/<int:student_id>', methods=['GET'])
@handle_errors
def get_student_notifications(student_id):
    """Get notifications relevant to a specific student"""
    # Get student details
    student_result = supabase.table('students').select('course_id, current_semester').eq('id', student_id).execute()
    if not student_result.data:
        return jsonify({"success": False, "error": "Student not found"}), 404

    student = student_result.data[0]

    # Get notifications for this student
    query = supabase.table('notifications').select('*').eq('is_active', True)

    # Build OR condition for notifications that apply to this student
    conditions = [
        'target_audience.eq.all',
        'target_audience.eq.students',
        f'and(target_audience.eq.specific,target_course_id.eq.{student["course_id"]})'
    ]

    # Add semester-specific notifications if applicable
    if student['current_semester']:
        conditions.append(f'and(target_audience.eq.specific,target_course_id.eq.{student["course_id"]},target_semester.eq.{student["current_semester"]})')

    query = query.or_(','.join(conditions))

    result = query.order('created_at', desc=True).execute()
    return jsonify({"success": True, "data": result.data})

@notifications_bp.route('/notifications/faculty/<int:faculty_id>', methods=['GET'])
@handle_errors
def get_faculty_notifications(faculty_id):
    """Get notifications relevant to a specific faculty member"""
    # Validate faculty exists
    faculty_result = supabase.table('faculty').select('id').eq('id', faculty_id).execute()
    if not faculty_result.data:
        return jsonify({"success": False, "error": "Faculty not found"}), 404

    # Get notifications for faculty
    result = supabase.table('notifications').select('*').eq('is_active', True).or_('target_audience.eq.all,target_audience.eq.faculty').order('created_at', desc=True).execute()

    return jsonify({"success": True, "data": result.data})

# Notification Analytics
@notifications_bp.route('/notifications/analytics', methods=['GET'])
@handle_errors
def get_notification_analytics():
    """Get notification analytics and statistics"""
    # Get all notifications
    all_notifications = supabase.table('notifications').select('*').execute()

    if not all_notifications.data:
        return jsonify({
            "success": True,
            "data": {
                "total_notifications": 0,
                "active_notifications": 0,
                "inactive_notifications": 0,
                "by_type": {},
                "by_audience": {},
                "recent_notifications": []
            }
        })

    notifications = all_notifications.data
    total_notifications = len(notifications)

    # Calculate statistics
    active_notifications = len([n for n in notifications if n['is_active']])
    inactive_notifications = total_notifications - active_notifications

    # Group by notification type
    by_type = {}
    for notification in notifications:
        notification_type = notification['notification_type']
        by_type[notification_type] = by_type.get(notification_type, 0) + 1

    # Group by target audience
    by_audience = {}
    for notification in notifications:
        audience = notification['target_audience']
        by_audience[audience] = by_audience.get(audience, 0) + 1

    # Get recent notifications (last 10)
    recent_notifications = sorted(notifications, key=lambda x: x['created_at'], reverse=True)[:10]

    # Calculate potential reach for each notification
    for notification in recent_notifications:
        if notification['target_audience'] == 'all':
            students_count = supabase.table('students').select('id', count='exact').execute().count or 0
            faculty_count = supabase.table('faculty').select('id', count='exact').execute().count or 0
            notification['potential_reach'] = students_count + faculty_count
        elif notification['target_audience'] == 'students':
            notification['potential_reach'] = supabase.table('students').select('id', count='exact').execute().count or 0
        elif notification['target_audience'] == 'faculty':
            notification['potential_reach'] = supabase.table('faculty').select('id', count='exact').execute().count or 0
        elif notification['target_audience'] == 'specific' and notification['target_course_id']:
            query = supabase.table('students').select('id', count='exact').eq('course_id', notification['target_course_id'])
            if notification['target_semester']:
                query = query.eq('current_semester', notification['target_semester'])
            notification['potential_reach'] = query.execute().count or 0
        else:
            notification['potential_reach'] = 0

    analytics = {
        'total_notifications': total_notifications,
        'active_notifications': active_notifications,
        'inactive_notifications': inactive_notifications,
        'by_type': by_type,
        'by_audience': by_audience,
        'recent_notifications': recent_notifications
    }

    return jsonify({"success": True, "data": analytics})

# Notification Templates (Mock data for now)
@notifications_bp.route('/notifications/templates', methods=['GET'])
@handle_errors
def get_notification_templates():
    """Get notification templates"""
    templates = [
        {
            'id': 'exam_reminder',
            'name': 'Exam Reminder',
            'title': 'Upcoming Exam: {exam_name}',
            'message': 'Dear {student_name},\n\nThis is a reminder for your upcoming {exam_name} exam on {exam_date} at {exam_time}.\n\nGood luck!',
            'variables': ['exam_name', 'exam_date', 'exam_time', 'student_name'],
            'notification_type': 'academic'
        },
        {
            'id': 'fee_reminder',
            'name': 'Fee Payment Reminder',
            'title': 'Fee Payment Due',
            'message': 'Dear {student_name},\n\nThis is a reminder that your fee payment of ₹{amount} is due on {due_date}.\n\nPlease make the payment at your earliest convenience.',
            'variables': ['student_name', 'amount', 'due_date'],
            'notification_type': 'administrative'
        },
        {
            'id': 'general_announcement',
            'name': 'General Announcement',
            'title': '{announcement_title}',
            'message': '{announcement_message}',
            'variables': ['announcement_title', 'announcement_message'],
            'notification_type': 'general'
        }
    ]

    return jsonify({"success": True, "data": templates})
