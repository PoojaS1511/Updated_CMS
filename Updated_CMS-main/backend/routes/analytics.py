from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from supabase_client import get_supabase
from functools import wraps

analytics_bp = Blueprint('analytics', __name__)

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    return wrapper

@analytics_bp.route('/admission', methods=['GET'])
@handle_errors
def get_admission_analytics():
    """
    Get admission analytics with optional filters
    Query Parameters:
    - start_date: Filter applications submitted after this date (YYYY-MM-DD)
    - end_date: Filter applications submitted before this date (YYYY-MM-DD)
    - statuses: Comma-separated list of statuses to include (pending,approved,rejected)
    - courses: Comma-separated list of course IDs to filter by
    - sources: Comma-separated list of sources to filter by
    """
    try:
        # Get query parameters with defaults
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        statuses = request.args.get('statuses', '').split(',')
        courses = request.args.get('courses', '').split(',')
        sources = request.args.get('sources', '').split(',')
        
        # Clean up empty strings from split
        statuses = [s for s in statuses if s]
        courses = [c for c in courses if c]
        sources = [s for s in sources if s]
        
        # Get Supabase client
        supabase = get_supabase()
        
        # Build the base query
        query = supabase.table('admissions').select('*')
        
        # Apply date filters
        if start_date:
            query = query.gte('created_at', f"{start_date}T00:00:00")
        if end_date:
            query = query.lte('created_at', f"{end_date}T23:59:59.999")
            
        # Apply status filter if provided
        if statuses:
            query = query.in_('status', statuses)
            
        # Execute the query to get filtered applications
        result = query.execute()
        applications = result.data if result.data else []
        
        # Process the data for analytics
        status_summary = {
            'total_applications': len(applications),
            'pending_applications': len([a for a in applications if a.get('status') == 'pending']),
            'approved_applications': len([a for a in applications if a.get('status') == 'approved']),
            'rejected_applications': len([a for a in applications if a.get('status') == 'rejected']),
        }
        monthly_trends = get_monthly_trends(applications)
        course_distribution = get_course_distribution(applications, courses)
        source_distribution = get_source_distribution(applications, sources)
        
        # Return the analytics data
        return jsonify({
            'status_summary': status_summary,
            'monthly_trends': monthly_trends,
            'course_distribution': course_distribution,
            'source_distribution': source_distribution
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch admission analytics'
        }), 500

def get_monthly_trends(applications):
    """Group applications by month and status"""
    monthly_data = {}
    
    for app in applications:
        if not app.get('created_at'):
            continue
            
        # Parse the date and create a month-year key
        try:
            app_date = datetime.fromisoformat(app['created_at'].replace('Z', '+00:00'))
            month_key = app_date.strftime('%Y-%m')
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': app_date.strftime('%b %Y'),
                    'applications': 0,
                    'approved': 0,
                    'rejected': 0
                }
                
            monthly_data[month_key]['applications'] += 1
            
            if app.get('status') == 'approved':
                monthly_data[month_key]['approved'] += 1
            elif app.get('status') == 'rejected':
                monthly_data[month_key]['rejected'] += 1
                
        except (ValueError, KeyError):
            continue
    
    # Convert to list and sort by month
    result = sorted(monthly_data.values(), key=lambda x: x['month'])
    return result

def get_course_distribution(applications, filter_courses=None):
    """Group applications by course"""
    course_counts = {}
    
    for app in applications:
        course_id = app.get('course_id')
        course_name = app.get('course_name', f'Course {course_id}')
        
        # Skip if course is filtered out
        if filter_courses and course_id not in filter_courses:
            continue
            
        if course_id not in course_counts:
            course_counts[course_id] = {
                'course': course_name,
                'applications': 0
            }
            
        course_counts[course_id]['applications'] += 1
    
    # Convert to list and sort by count (descending)
    result = sorted(course_counts.values(), key=lambda x: -x['applications'])
    return result

def get_source_distribution(applications, filter_sources=None):
    """Group applications by source"""
    source_counts = {}
    
    for app in applications:
        source = app.get('source', 'Unknown')
        
        # Skip if source is filtered out
        if filter_sources and source not in filter_sources:
            continue
            
        if source not in source_counts:
            source_counts[source] = 0
            
        source_counts[source] += 1
    
    # Convert to list of {source, count} objects and sort by count (descending)
    result = [
        {'source': source, 'count': count}
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1])
    ]
    
    return result

@analytics_bp.route('/performance', methods=['GET'])
def get_performance_analytics():
    try:
        # Get current academic year
        current_year = datetime.now().year
        
        # Course performance metrics
        course_performance = supabase.rpc('get_course_performance_metrics', {
            'academic_year': current_year
        }).execute()
        
        # Performance trends over time
        performance_trends = supabase.rpc('get_performance_trends', {
            'academic_year': current_year
        }).execute()
        
        # Top performers
        top_performers = supabase.rpc('get_top_performers', {
            'academic_year': current_year,
            'limit': 5
        }).execute()
        
        return jsonify({
            'success': True,
            'data': {
                'course_performance': course_performance.data,
                'performance_trends': performance_trends.data,
                'top_performers': top_performers.data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/utilization', methods=['GET'])
def get_utilization_analytics():
    try:
        # Room utilization
        room_utilization = supabase.rpc('get_room_utilization').execute()
        
        # Resource utilization
        resource_utilization = supabase.rpc('get_resource_utilization').execute()
        
        # Daily utilization trend (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        daily_utilization = supabase.rpc('get_daily_utilization_trend', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }).execute()
        
        # Utilization summary
        utilization_summary = supabase.rpc('get_utilization_summary').execute()
        
        return jsonify({
            'success': True,
            'data': {
                'room_utilization': room_utilization.data,
                'resource_utilization': resource_utilization.data,
                'daily_utilization': daily_utilization.data,
                'utilization_summary': utilization_summary.data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
