from flask import Blueprint, request, jsonify, g
from supabase_client import get_supabase
from datetime import datetime, time
from functools import wraps
from typing import Dict, List, Optional, Any
import uuid

# Import models
from models.exam import ExamCreate, ExamUpdate, ExamInDB

exams_bp = Blueprint('exams', __name__)

# Initialize Supabase client
supabase = get_supabase()

def handle_db_error(e):
    """Handle database errors gracefully"""
    print(f"Database error: {str(e)}")
    return jsonify({"error": "A database error occurred"}), 500

def validate_exam_data(data: Dict[str, Any], is_update: bool = False) -> Optional[Dict[str, str]]:
    """Validate exam data"""
    errors = {}
    
    if not is_update or 'name' in data:
        if not data.get('name'):
            errors['name'] = 'Exam name is required'
    
    if not is_update or 'subject_id' in data:
        if not data.get('subject_id'):
            errors['subject_id'] = 'Subject is required'
    
    if not is_update or 'date' in data:
        try:
            datetime.strptime(data.get('date', ''), '%Y-%m-%d')
        except (ValueError, TypeError):
            errors['date'] = 'Invalid date format. Use YYYY-MM-DD'
    
    for time_field in ['start_time', 'end_time']:
        if not is_update or time_field in data:
            try:
                time.fromisoformat(data.get(time_field, ''))
            except (ValueError, TypeError):
                errors[time_field] = f'Invalid {time_field} format. Use HH:MM:SS'
    
    if not is_update or 'duration' in data:
        try:
            duration = int(data.get('duration', 0))
            if duration <= 0:
                errors['duration'] = 'Duration must be a positive number'
        except (ValueError, TypeError):
            errors['duration'] = 'Duration must be a number'
    
    if not is_update or 'max_marks' in data:
        try:
            max_marks = int(data.get('max_marks', 0))
            if max_marks <= 0:
                errors['max_marks'] = 'Maximum marks must be a positive number'
        except (ValueError, TypeError):
            errors['max_marks'] = 'Maximum marks must be a number'
    
    if not is_update or 'passing_marks' in data:
        try:
            passing_marks = int(data.get('passing_marks', 0))
            max_marks = int(data.get('max_marks', 0))
            if passing_marks < 0:
                errors['passing_marks'] = 'Passing marks cannot be negative'
            if passing_marks > max_marks:
                errors['passing_marks'] = 'Passing marks cannot be greater than maximum marks'
        except (ValueError, TypeError):
            errors['passing_marks'] = 'Passing marks must be a number'
    
    return errors if errors else None

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return handle_db_error(e)
    return wrapper

@exams_bp.route('/exams', methods=['GET'])
@handle_errors
def get_exams():
    """Get all exams with optional filtering"""
    query = supabase.table('exams').select('''
        *,
        subjects (
            id,
            name,
            code,
            courses (
                name,
                code
            )
        )
    ''')

    # Add filters if provided
    if request.args.get('subject_id'):
        query = query.eq('subject_id', request.args.get('subject_id'))
    if request.args.get('exam_type'):
        query = query.eq('exam_type', request.args.get('exam_type'))
    if request.args.get('academic_year'):
        query = query.eq('academic_year', request.args.get('academic_year'))
    if request.args.get('semester'):
        query = query.eq('semester', request.args.get('semester'))
    if request.args.get('search'):
        search_term = request.args.get('search')
        query = query.ilike('name', f'%{search_term}%')

    result = query.order('date', desc=True).execute()
    return jsonify({"success": True, "data": result.data})

@exams_bp.route('/exams/<int:exam_id>', methods=['GET'])
@handle_errors
def get_exam(exam_id):
    """Get a single exam by ID"""
    result = supabase.table('exams').select('''
        *,
        subjects (
            id,
            name,
            code,
            courses (
                name,
                code
            )
        )
    ''').eq('id', exam_id).execute()

    if not result.data:
        return jsonify({"success": False, "error": "Exam not found"}), 404

    return jsonify({"success": True, "data": result.data[0]})

@exams_bp.route('/exams', methods=['POST'])
@handle_errors
def create_exam():
    """Create a new exam"""
    data = request.get_json()
    required_fields = ['name', 'exam_type', 'subject_id', 'date', 'start_time', 'academic_year', 'semester']

    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    # Validate exam_type
    valid_exam_types = ['IA1', 'IA2', 'model', 'final']
    if data['exam_type'] not in valid_exam_types:
        return jsonify({"success": False, "error": f"Invalid exam_type. Must be one of: {valid_exam_types}"}), 400

    # Check if subject exists
    subject_result = supabase.table('subjects').select('id').eq('id', data['subject_id']).execute()
    if not subject_result.data:
        return jsonify({"success": False, "error": "Invalid subject_id"}), 400

    exam_data = {
        'name': data['name'],
        'exam_type': data['exam_type'],
        'subject_id': data['subject_id'],
        'date': data['date'],
        'start_time': data['start_time'],
        'duration_minutes': data.get('duration_minutes', 180),
        'max_marks': data.get('max_marks', 100),
        'academic_year': data['academic_year'],
        'semester': data['semester'],
        'created_at': datetime.now().isoformat()
    }

    result = supabase.table('exams').insert(exam_data).execute()
    return jsonify({"success": True, "data": result.data[0] if result.data else {}}), 201

@exams_bp.route('/exams/<int:exam_id>', methods=['PUT'])
@handle_errors
def update_exam(exam_id):
    """Update an existing exam"""
    data = request.get_json()

    # Validate exam_type if provided
    if 'exam_type' in data:
        valid_exam_types = ['IA1', 'IA2', 'model', 'final']
        if data['exam_type'] not in valid_exam_types:
            return jsonify({"success": False, "error": f"Invalid exam_type. Must be one of: {valid_exam_types}"}), 400

    # Check if subject exists if provided
    if 'subject_id' in data:
        subject_result = supabase.table('subjects').select('id').eq('id', data['subject_id']).execute()
        if not subject_result.data:
            return jsonify({"success": False, "error": "Invalid subject_id"}), 400

    result = supabase.table('exams').update(data).eq('id', exam_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Exam not found"}), 404

    return jsonify({"success": True, "data": result.data[0]})

@exams_bp.route('/exams/<int:exam_id>', methods=['DELETE'])
@handle_errors
def delete_exam(exam_id):
    """Delete an exam"""
    # Check if there are any marks for this exam
    marks = supabase.table('marks').select('id').eq('exam_id', exam_id).execute()
    if marks.data:
        return jsonify({
            "success": False,
            "error": "Cannot delete exam with associated marks"
        }), 400

    result = supabase.table('exams').delete().eq('id', exam_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Exam not found"}), 404

    return jsonify({"success": True, "message": "Exam deleted successfully"})

# Marks Entry System
@exams_bp.route('/marks', methods=['GET'])
@handle_errors
def get_marks():
    """Get all marks with optional filtering"""
    query = supabase.table('marks').select('''
        *,
        students (
            id,
            register_number,
            full_name
        ),
        exams (
            id,
            name,
            exam_type,
            date
        ),
        subjects (
            id,
            name,
            code
        )
    ''')

    # Add filters if provided
    if request.args.get('student_id'):
        query = query.eq('student_id', request.args.get('student_id'))
    if request.args.get('exam_id'):
        query = query.eq('exam_id', request.args.get('exam_id'))
    if request.args.get('subject_id'):
        query = query.eq('subject_id', request.args.get('subject_id'))

    result = query.order('created_at', desc=True).execute()
    return jsonify({"success": True, "data": result.data})

@exams_bp.route('/marks', methods=['POST'])
@handle_errors
def create_marks():
    """Create marks entry"""
    data = request.get_json()
    required_fields = ['student_id', 'exam_id', 'subject_id', 'marks_obtained']

    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    # Validate student exists
    student_result = supabase.table('students').select('id').eq('id', data['student_id']).execute()
    if not student_result.data:
        return jsonify({"success": False, "error": "Invalid student_id"}), 400

    # Validate exam exists
    exam_result = supabase.table('exams').select('id, max_marks').eq('id', data['exam_id']).execute()
    if not exam_result.data:
        return jsonify({"success": False, "error": "Invalid exam_id"}), 400

    # Validate subject exists
    subject_result = supabase.table('subjects').select('id').eq('id', data['subject_id']).execute()
    if not subject_result.data:
        return jsonify({"success": False, "error": "Invalid subject_id"}), 400

    # Check if marks already exist for this combination
    existing_marks = supabase.table('marks').select('id').eq('student_id', data['student_id']).eq('exam_id', data['exam_id']).eq('subject_id', data['subject_id']).execute()
    if existing_marks.data:
        return jsonify({"success": False, "error": "Marks already exist for this student, exam, and subject"}), 400

    max_marks = exam_result.data[0]['max_marks']
    marks_obtained = float(data['marks_obtained'])

    # Calculate grade and grade points
    percentage = (marks_obtained / max_marks) * 100
    grade, grade_points = calculate_grade(percentage)

    marks_data = {
        'student_id': data['student_id'],
        'exam_id': data['exam_id'],
        'subject_id': data['subject_id'],
        'marks_obtained': marks_obtained,
        'max_marks': max_marks,
        'grade': grade,
        'grade_points': grade_points,
        'remarks': data.get('remarks'),
        'created_at': datetime.now().isoformat()
    }

    result = supabase.table('marks').insert(marks_data).execute()
    return jsonify({"success": True, "data": result.data[0] if result.data else {}}), 201

def calculate_grade(percentage):
    """Calculate grade and grade points based on percentage"""
    if percentage >= 90:
        return 'A+', 10.0
    elif percentage >= 80:
        return 'A', 9.0
    elif percentage >= 70:
        return 'B+', 8.0
    elif percentage >= 60:
        return 'B', 7.0
    elif percentage >= 50:
        return 'C+', 6.0
    elif percentage >= 40:
        return 'C', 5.0
    else:
        return 'F', 0.0

@exams_bp.route('/marks/<int:marks_id>', methods=['PUT'])
@handle_errors
def update_marks(marks_id):
    """Update marks entry"""
    data = request.get_json()

    # If marks_obtained is being updated, recalculate grade
    if 'marks_obtained' in data:
        # Get the max_marks for this entry
        marks_result = supabase.table('marks').select('max_marks').eq('id', marks_id).execute()
        if not marks_result.data:
            return jsonify({"success": False, "error": "Marks entry not found"}), 404

        max_marks = marks_result.data[0]['max_marks']
        marks_obtained = float(data['marks_obtained'])
        percentage = (marks_obtained / max_marks) * 100
        grade, grade_points = calculate_grade(percentage)

        data['grade'] = grade
        data['grade_points'] = grade_points

    result = supabase.table('marks').update(data).eq('id', marks_id).execute()
    if not result.data:
        return jsonify({"success": False, "error": "Marks entry not found"}), 404

    return jsonify({"success": True, "data": result.data[0]})

# Exam Analytics
@exams_bp.route('/analytics/exam/<int:exam_id>', methods=['GET'])
@handle_errors
def get_exam_analytics(exam_id):
    """Get analytics for a specific exam"""
    # Get all marks for this exam
    marks_result = supabase.table('marks').select('''
        marks_obtained,
        max_marks,
        grade,
        students (
            full_name,
            register_number
        )
    ''').eq('exam_id', exam_id).execute()

    if not marks_result.data:
        return jsonify({"success": False, "error": "No marks found for this exam"}), 404

    marks_data = marks_result.data
    total_students = len(marks_data)

    if total_students == 0:
        return jsonify({"success": True, "data": {"message": "No students have taken this exam yet"}})

    # Calculate statistics
    marks_list = [float(mark['marks_obtained']) for mark in marks_data]
    max_marks = marks_data[0]['max_marks']

    highest_marks = max(marks_list)
    lowest_marks = min(marks_list)
    average_marks = sum(marks_list) / len(marks_list)

    # Calculate pass percentage (assuming 40% is passing)
    passing_marks = max_marks * 0.4
    passed_students = len([mark for mark in marks_list if mark >= passing_marks])
    pass_percentage = (passed_students / total_students) * 100

    # Grade distribution
    grade_distribution = {}
    for mark in marks_data:
        grade = mark['grade']
        grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

    analytics = {
        'total_students': total_students,
        'highest_marks': highest_marks,
        'lowest_marks': lowest_marks,
        'average_marks': round(average_marks, 2),
        'pass_percentage': round(pass_percentage, 2),
        'passed_students': passed_students,
        'failed_students': total_students - passed_students,
        'grade_distribution': grade_distribution,
        'marks_distribution': marks_data
    }

    return jsonify({"success": True, "data": analytics})

@exams_bp.route('/analytics/subject/<int:subject_id>', methods=['GET'])
@handle_errors
def get_subject_analytics(subject_id):
    """Get analytics for all exams of a specific subject"""
    # Get all exams for this subject
    exams_result = supabase.table('exams').select('id, name, exam_type, date').eq('subject_id', subject_id).execute()

    if not exams_result.data:
        return jsonify({"success": False, "error": "No exams found for this subject"}), 404

    subject_analytics = []

    for exam in exams_result.data:
        # Get marks for each exam
        marks_result = supabase.table('marks').select('marks_obtained, max_marks').eq('exam_id', exam['id']).execute()

        if marks_result.data:
            marks_list = [float(mark['marks_obtained']) for mark in marks_result.data]
            max_marks = marks_result.data[0]['max_marks']

            average_marks = sum(marks_list) / len(marks_list)
            passing_marks = max_marks * 0.4
            passed_students = len([mark for mark in marks_list if mark >= passing_marks])
            pass_percentage = (passed_students / len(marks_list)) * 100

            exam_analytics = {
                'exam_id': exam['id'],
                'exam_name': exam['name'],
                'exam_type': exam['exam_type'],
                'date': exam['date'],
                'total_students': len(marks_list),
                'average_marks': round(average_marks, 2),
                'pass_percentage': round(pass_percentage, 2),
                'highest_marks': max(marks_list),
                'lowest_marks': min(marks_list)
            }

            subject_analytics.append(exam_analytics)

    return jsonify({"success": True, "data": subject_analytics})
