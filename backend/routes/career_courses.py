# backend/routes/career_courses.py
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

bp = Blueprint('career_courses', __name__)

# Table name for career courses
COURSES_TABLE = 'career_courses'

# Sample data for demonstration
SAMPLE_COURSES = [
    {
        "title": "Python for Beginners - Full Course",
        "platform": "youtube",
        "embed_url": "https://www.youtube.com/embed/rfscVS0vtbw",
        "description": "Learn Python from scratch with this comprehensive tutorial.",
        "level": "Beginner",
        "external_url": "https://www.youtube.com/watch?v=rfscVS0vtbw"
    },
    {
        "title": "Web Development Bootcamp",
        "platform": "udemy",
        "embed_url": "https://www.udemy.com/embed/web-development-bootcamp",
        "description": "Full stack web development course covering HTML, CSS, JavaScript, and more.",
        "level": "Beginner",
        "external_url": "https://www.udemy.com/web-development-bootcamp"
    }
]

@bp.route('/api/career/courses', methods=['GET'])
def get_courses():
    """Get all career courses with optional filtering"""
    try:
        # Query courses from Supabase
        response = current_app.supabase.table(COURSES_TABLE).select('*').execute()
        if not response.data:
            # If no courses in Supabase, add sample data
            for course_data in SAMPLE_COURSES:
                course_data.update({
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                })
                current_app.supabase.table(COURSES_TABLE).insert(course_data).execute()
            response = current_app.supabase.table(COURSES_TABLE).select('*').execute()
        return jsonify(response.data)
    except Exception as e:
        # Fallback to sample data if Supabase is not available
        print(f"Error fetching courses: {str(e)}")
        return jsonify(SAMPLE_COURSES)

@bp.route('/api/career/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get a specific career course by ID"""
    try:
        response = current_app.supabase.table(COURSES_TABLE).select('*').eq('id', course_id).execute()
        if not response.data:
            return jsonify({'error': 'Course not found'}), 404
        return jsonify(response.data[0])
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@bp.route('/api/career/courses', methods=['POST'])
def add_course():
    """Add a new career course"""
    try:
        data = request.json
        required_fields = ['title', 'platform', 'external_url']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        data.update({
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        response = current_app.supabase.table(COURSES_TABLE).insert(data).execute()
        return jsonify(response.data[0]), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/career/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    """Update an existing career course"""
    try:
        response = current_app.supabase.table(COURSES_TABLE).select('*').eq('id', course_id).execute()
        if not response.data:
            return jsonify({'error': 'Course not found'}), 404
        data = request.json
        data.update({
            'updated_at': datetime.utcnow().isoformat()
        })
        response = current_app.supabase.table(COURSES_TABLE).update(data).eq('id', course_id).execute()
        return jsonify(response.data[0])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/career/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    """Delete a career course"""
    try:
        response = current_app.supabase.table(COURSES_TABLE).select('*').eq('id', course_id).execute()
        if not response.data:
            return jsonify({'error': 'Course not found'}), 404
        current_app.supabase.table(COURSES_TABLE).delete().eq('id', course_id).execute()
        return jsonify({'message': 'Course deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/career/courses/filters', methods=['GET'])
def get_filters():
    """Get available filter options"""
    try:
        # Default values
        platforms = ['Udemy', 'YouTube', 'Coursera', 'edX', 'Pluralsight']
        difficulties = ['Beginner', 'Intermediate', 'Advanced', 'All Levels']
        categories = [
            'Development', 'Business', 'IT & Software',
            'Office Productivity', 'Personal Development', 'Design', 'Marketing',
            'Lifestyle', 'Photography & Video', 'Health & Fitness', 'Music',
            'Teaching & Academics', 'Data Science', 'Programming', 'Web Development',
            'Mobile Development', 'Game Development', 'Cloud Computing', 'Cybersecurity'
        ]
        
        # Try to get unique values from Supabase if available
        try:
            # Get unique categories
            categories_resp = current_app.supabase.table(COURSES_TABLE).select('category').not_.is_('category', 'null').execute()
            if categories_resp.data:
                db_categories = list(set([c['category'] for c in categories_resp.data if c.get('category')]))
                categories = list(set(categories + db_categories))
                
            # Get unique platforms
            platforms_resp = current_app.supabase.table(COURSES_TABLE).select('platform').not_.is_('platform', 'null').execute()
            if platforms_resp.data:
                db_platforms = list(set([p['platform'] for p in platforms_resp.data if p.get('platform')]))
                platforms = list(set(platforms + db_platforms))
                
            # Get unique difficulties
            difficulties_resp = current_app.supabase.table(COURSES_TABLE).select('level').not_.is_('level', 'null').execute()
            if difficulties_resp.data:
                db_difficulties = list(set([d['level'] for d in difficulties_resp.data if d.get('level')]))
                difficulties = list(set(difficulties + db_difficulties))
                
        except Exception as db_error:
            print(f"Error fetching filter options from database: {db_error}")
            # Continue with default values if there's an error
        
        return jsonify({
            'success': True,
            'data': {
                'categories': sorted(categories),
                'platforms': sorted(platforms),
                'difficulties': sorted(difficulties)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500