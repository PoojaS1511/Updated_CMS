"""
Career Roadmap Routes
Handles career assistant functionality including roadmap generation and AI mentor chat
"""
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from supabase_client import get_supabase
import logging
from datetime import datetime
import json
import os

# Try to import Gemini AI
try:
    import google.generativeai as genai
    genai_available = True
except ImportError:
    genai = None
    genai_available = False

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create blueprint
career_roadmap_bp = Blueprint('career_roadmap', __name__)

# Initialize Supabase
supabase = get_supabase()

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or "AIzaSyCHUFZItopFXXiupZ7KQJb4APnWA5I_UXs"
if genai_available:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Use gemini-1.5-flash instead of gemini-pro
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info(f"Gemini AI configured successfully with gemini-1.5-flash (API key: {GEMINI_API_KEY[:20]}...)")
    except Exception as e:
        logger.error(f"Failed to configure Gemini AI: {e}")
        genai_available = False
        model = None
else:
    model = None
    logger.warning("Gemini AI not available - google.generativeai not installed")


def generate_roadmap_with_ai(career_interest: str, weeks: int = 10) -> list:
    """
    Generate a career roadmap using Gemini AI
    
    Args:
        career_interest: The career field (e.g., "AI Engineer")
        weeks: Number of weeks for the roadmap (default: 10)
    
    Returns:
        List of roadmap steps with week_no, topic, description, milestone
    """
    if not genai_available or not model:
        logger.warning("Gemini AI not available, returning fallback roadmap")
        return generate_fallback_roadmap(career_interest, weeks)
    
    try:
        prompt = f"""
You are a career guidance expert. Generate a detailed {weeks}-week learning roadmap for someone who wants to become a {career_interest}.

For each week, provide:
1. Week number (1 to {weeks})
2. Topic/Focus area
3. Brief description (2-3 sentences, actionable and specific)
4. Milestone (what should be achieved by end of week)

Format your response as a JSON array with this exact structure:
[
  {{
    "week_no": 1,
    "topic": "Topic name",
    "description": "Brief actionable description with specific tasks and learning objectives",
    "milestone": "Concrete achievement or deliverable for this week"
  }}
]

Make it practical, beginner-friendly, and progressive. Focus on hands-on learning with specific tasks.
Return ONLY the JSON array, no additional text or markdown formatting.
"""

        logger.info(f"Generating roadmap with Gemini AI for: {career_interest}, {weeks} weeks")
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        logger.info(f"Gemini AI raw response: {response_text[:200]}...")

        # Try to extract JSON from response
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        # Parse JSON
        roadmap_steps = json.loads(response_text)

        # Validate structure
        if not isinstance(roadmap_steps, list):
            raise ValueError("Response is not a list")

        # Ensure all required fields are present
        for step in roadmap_steps:
            if not all(key in step for key in ['week_no', 'topic', 'description', 'milestone']):
                raise ValueError("Missing required fields in roadmap step")

        logger.info(f"Successfully generated {len(roadmap_steps)} roadmap steps with Gemini AI")
        return roadmap_steps
        
    except Exception as e:
        logger.error(f"Error generating roadmap with AI: {e}")
        return generate_fallback_roadmap(career_interest, weeks)


def generate_fallback_roadmap(career_interest: str, weeks: int = 10) -> list:
    """Generate a basic fallback roadmap when AI is not available"""
    roadmap = []
    topics = [
        "Fundamentals & Basics",
        "Core Concepts",
        "Practical Applications",
        "Tools & Technologies",
        "Hands-on Projects",
        "Advanced Topics",
        "Industry Best Practices",
        "Portfolio Building",
        "Interview Preparation",
        "Continuous Learning"
    ]

    logger.info(f"Generating fallback roadmap for: {career_interest}, {weeks} weeks")

    for i in range(min(weeks, len(topics))):
        roadmap.append({
            "week_no": i + 1,
            "topic": f"{topics[i]} - {career_interest}",
            "description": f"Learn and practice {topics[i].lower()} related to {career_interest}. Focus on understanding key principles and building practical skills.",
            "milestone": f"Complete exercises and mini-projects related to {topics[i].lower()}"
        })

    return roadmap


@career_roadmap_bp.route('/generate', methods=['POST'])
def generate_roadmap():
    """
    POST /api/roadmap/generate
    Generate a new career roadmap for a student
    
    Request body:
    {
        "student_id": "uuid",
        "career_interest": "AI Engineer",
        "description": "Optional description",
        "weeks": 10
    }
    """
    try:
        print("\n=== DEBUG: generate_roadmap endpoint hit ===")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request data: {request.get_data()}")
        
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            print("Handling OPTIONS request")
            response = jsonify({"status": "preflight"})
            origin = request.headers.get('Origin', 'http://localhost:3001')
            allowed_origins = ['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000', 'http://127.0.0.1:3001']
            if origin in allowed_origins:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        print(f"Parsed JSON data: {data}")
        
        student_id = data.get('student_id')
        career_interest = data.get('career_interest')
        description = data.get('description', '')
        weeks = data.get('weeks', 10)
        
        print(f"Student ID: {student_id}")
        print(f"Career Interest: {career_interest}")
        print(f"Description: {description}")
        print(f"Weeks: {weeks}")
        
        # Print environment variables for debugging
        print("\nEnvironment Variables:")
        print(f"FLASK_ENV: {os.environ.get('FLASK_ENV')}")
        print(f"DEBUG: {os.environ.get('DEBUG')}")
        print("\nRequest Environment:")
        print(f"REQUEST_METHOD: {request.environ.get('REQUEST_METHOD')}")
        print(f"PATH_INFO: {request.environ.get('PATH_INFO')}")
        print(f"QUERY_STRING: {request.environ.get('QUERY_STRING')}")
        print(f"CONTENT_TYPE: {request.environ.get('CONTENT_TYPE')}")
        print(f"HTTP_ORIGIN: {request.environ.get('HTTP_ORIGIN')}")
        print(f"HTTP_ACCESS_CONTROL_REQUEST_METHOD: {request.environ.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')}")
        print(f"HTTP_ACCESS_CONTROL_REQUEST_HEADERS: {request.environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS')}")
        print("\nRegistered routes:")
        for rule in current_app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule.rule} {list(rule.methods)}")
        print("\n")
        
        if not student_id or not career_interest:
            return jsonify({'error': 'student_id and career_interest are required'}), 400

        # Validate student exists and get actual student ID
        # The frontend sends user_id from Supabase auth, we need to get the student's id
        try:
            # First try to find by user_id (from Supabase auth)
            student_result = supabase.table('students').select('id, user_id, full_name').eq('user_id', student_id).execute()

            # If not found by user_id, try by id directly
            if not student_result.data:
                student_result = supabase.table('students').select('id, user_id, full_name').eq('id', student_id).execute()

            if not student_result.data:
                logger.error(f"Student not found with ID: {student_id}")
                return jsonify({
                    'success': False,
                    'error': 'Student not found',
                    'details': f'No student found with ID or user_id: {student_id}'
                }), 404

            # Use the actual student.id for database operations
            actual_student_id = student_result.data[0]['id']
            logger.info(f"Found student: {student_result.data[0].get('full_name', 'Unknown')} (ID: {actual_student_id})")

        except Exception as e:
            logger.error(f"Error verifying student: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Error verifying student',
                'details': str(e)
            }), 500
        
        # Validate weeks
        if not isinstance(weeks, int) or weeks < 4 or weeks > 20:
            weeks = 10

        logger.info(f"Generating roadmap for student {actual_student_id}, interest: {career_interest}")

        # Generate roadmap using AI first (before any DB operations)
        try:
            logger.info(f"Calling generate_roadmap_with_ai for {career_interest}, {weeks} weeks")
            roadmap_steps = generate_roadmap_with_ai(career_interest, weeks)
            logger.info(f"Generated {len(roadmap_steps)} steps")
            logger.info(f"Sample step: {roadmap_steps[0] if roadmap_steps else 'No steps'}")
        except Exception as e:
            logger.error(f"Failed to generate roadmap with AI: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate roadmap',
                'details': f'AI generation error: {str(e)}'
            }), 503

        # Start transaction-like operation (Supabase doesn't support transactions directly in the Python client)
        try:
            # 1. Create career interest
            interest_data = {
                'student_id': actual_student_id,
                'interest_title': career_interest,
                'description': description
            }
            logger.info(f"Creating career interest: {interest_data}")

            try:
                interest_result = supabase.table('career_interests').insert(interest_data).execute()
                logger.info(f"Career interest result: {interest_result}")
            except Exception as e:
                logger.error(f"Error creating career interest: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
                raise

            if not interest_result.data:
                raise Exception('Failed to create career interest - no data returned')

            interest_id = interest_result.data[0]['id']
            logger.info(f"Created career interest with ID: {interest_id}")

            # 2. Create roadmap record
            roadmap_data = {
                'student_id': actual_student_id,
                'interest_id': interest_id,
                'roadmap_title': f"{career_interest} Learning Path",
                'total_weeks': len(roadmap_steps),
                'ai_generated': genai_available
            }
            logger.info(f"Creating roadmap: {roadmap_data}")

            try:
                roadmap_result = supabase.table('career_roadmaps').insert(roadmap_data).execute()
                logger.info(f"Roadmap result: {roadmap_result}")
            except Exception as e:
                logger.error(f"Error creating roadmap: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
                raise

            if not roadmap_result.data:
                raise Exception('Failed to create roadmap - no data returned')

            roadmap_id = roadmap_result.data[0]['id']
            logger.info(f"Created roadmap with ID: {roadmap_id}")

            # 3. Insert roadmap steps
            steps_to_insert = [{
                'roadmap_id': roadmap_id,
                'week_no': step['week_no'],
                'topic': step['topic'],
                'description': step['description'],
                'milestone': step['milestone'],
                'status': 'pending'
            } for step in roadmap_steps]

            logger.info(f"Inserting {len(steps_to_insert)} roadmap steps")
            logger.info(f"First step sample: {steps_to_insert[0] if steps_to_insert else 'No steps'}")

            try:
                steps_result = supabase.table('roadmap_steps').insert(steps_to_insert).execute()
                logger.info(f"Steps result: {steps_result}")
            except Exception as e:
                logger.error(f"Error creating roadmap steps: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
                raise

            if not steps_result.data:
                raise Exception('Failed to create roadmap steps - no data returned')

            logger.info(f"Successfully created roadmap {roadmap_id} with {len(steps_result.data)} steps")

            return jsonify({
                'success': True,
                'roadmap_id': roadmap_id,
                'interest_id': interest_id,
                'total_weeks': len(roadmap_steps),
                'message': 'Roadmap generated successfully'
            }), 201

        except Exception as e:
            # Log the error and provide a user-friendly message
            logger.error(f"Database error in roadmap generation: {str(e)}")
            logger.error(f"Full exception: {repr(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Check if it's a foreign key violation
            error_msg = str(e).lower()
            if 'foreign key' in error_msg and 'violates' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Invalid student reference',
                    'details': 'The provided student ID does not exist in our system.'
                }), 400

            return jsonify({
                'success': False,
                'error': 'Failed to generate roadmap',
                'details': f'Database error: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        return jsonify({'error': str(e)}), 500


@career_roadmap_bp.route('/<student_id>', methods=['GET'])
def get_student_roadmaps(student_id):
    """
    GET /api/roadmap/<student_id>
    Fetch all roadmaps for a student with progress calculation
    """
    try:
        # Get actual student ID (handle both user_id and student id)
        student_result = supabase.table('students').select('id').eq('user_id', student_id).execute()
        if not student_result.data:
            student_result = supabase.table('students').select('id').eq('id', student_id).execute()

        if not student_result.data:
            return jsonify({'roadmaps': []}), 200

        actual_student_id = student_result.data[0]['id']

        # Fetch all roadmaps for the student
        roadmaps_result = supabase.table('career_roadmaps')\
            .select('*, career_interests(interest_title, description)')\
            .eq('student_id', actual_student_id)\
            .order('created_at', desc=True)\
            .execute()

        if not roadmaps_result.data:
            return jsonify({'roadmaps': []}), 200
        
        roadmaps = []
        for roadmap in roadmaps_result.data:
            # Fetch steps for this roadmap
            steps_result = supabase.table('roadmap_steps')\
                .select('*')\
                .eq('roadmap_id', roadmap['id'])\
                .order('week_no')\
                .execute()
            
            total_steps = len(steps_result.data) if steps_result.data else 0
            completed_steps = sum(1 for step in steps_result.data if step['status'] == 'completed') if steps_result.data else 0
            progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
            
            roadmaps.append({
                **roadmap,
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'progress_percentage': round(progress_percentage, 1)
            })
        
        return jsonify({'roadmaps': roadmaps}), 200

    except Exception as e:
        logger.error(f"Error fetching roadmaps: {e}")
        return jsonify({'error': str(e)}), 500


@career_roadmap_bp.route('/steps/<roadmap_id>', methods=['GET'])
def get_roadmap_steps(roadmap_id):
    """
    GET /api/roadmap/steps/<roadmap_id>
    Fetch all steps for a specific roadmap
    """
    try:
        steps_result = supabase.table('roadmap_steps')\
            .select('*')\
            .eq('roadmap_id', roadmap_id)\
            .order('week_no')\
            .execute()

        if not steps_result.data:
            return jsonify({'steps': []}), 200

        return jsonify({'steps': steps_result.data}), 200

    except Exception as e:
        logger.error(f"Error fetching roadmap steps: {e}")
        return jsonify({'error': str(e)}), 500


@career_roadmap_bp.route('/steps/update-status', methods=['PATCH'])
def update_step_status():
    """
    PATCH /api/roadmap/steps/update-status
    Mark a roadmap step as completed or update its status

    Request body:
    {
        "step_id": "uuid",
        "status": "completed" | "in_progress" | "pending"
    }
    """
    try:
        data = request.get_json()
        step_id = data.get('step_id')
        status = data.get('status', 'completed')

        if not step_id:
            return jsonify({'error': 'step_id is required'}), 400

        if status not in ['pending', 'in_progress', 'completed']:
            return jsonify({'error': 'Invalid status. Must be pending, in_progress, or completed'}), 400

        # Update the step
        update_data = {
            'status': status
        }

        # If marking as completed, set completed_on timestamp
        if status == 'completed':
            update_data['completed_on'] = datetime.now().isoformat()
        elif status == 'pending':
            update_data['completed_on'] = None

        logger.info(f"Updating step {step_id} with data: {update_data}")

        try:
            result = supabase.table('roadmap_steps')\
                .update(update_data)\
                .eq('id', step_id)\
                .execute()

            logger.info(f"Update result: {result}")
        except Exception as e:
            logger.error(f"Error executing update: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        if not result.data:
            logger.warning(f"No data returned for step {step_id}")
            return jsonify({'error': 'Step not found or update failed'}), 404

        logger.info(f"Successfully updated step {step_id} to status: {status}")

        return jsonify({
            'success': True,
            'step': result.data[0],
            'message': f'Step marked as {status}'
        }), 200

    except Exception as e:
        logger.error(f"Error updating step status: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@career_roadmap_bp.route('/mentor/chat', methods=['POST'])
def mentor_chat():
    """
    POST /api/roadmap/mentor/chat
    Chat with AI mentor for career guidance

    Request body:
    {
        "student_id": "uuid",
        "roadmap_id": "uuid" (optional),
        "message": "User's question or message"
    }
    """
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        roadmap_id = data.get('roadmap_id')
        message = data.get('message')

        if not student_id or not message:
            return jsonify({'error': 'student_id and message are required'}), 400

        # Get actual student ID (handle both user_id and student id)
        student_result = supabase.table('students').select('id').eq('user_id', student_id).execute()
        if not student_result.data:
            student_result = supabase.table('students').select('id').eq('id', student_id).execute()

        if not student_result.data:
            return jsonify({'error': 'Student not found'}), 404

        actual_student_id = student_result.data[0]['id']

        # Get roadmap context if roadmap_id is provided
        context = ""
        if roadmap_id:
            # Fetch roadmap details
            roadmap_result = supabase.table('career_roadmaps')\
                .select('*, career_interests(interest_title)')\
                .eq('id', roadmap_id)\
                .single()\
                .execute()

            if roadmap_result.data:
                roadmap = roadmap_result.data
                career_title = roadmap.get('career_interests', {}).get('interest_title', 'your career')

                # Fetch roadmap steps
                steps_result = supabase.table('roadmap_steps')\
                    .select('week_no, topic, description, milestone, status')\
                    .eq('roadmap_id', roadmap_id)\
                    .order('week_no')\
                    .execute()

                if steps_result.data:
                    context = f"\n\nStudent's Career Goal: {career_title}\n"
                    context += f"Roadmap Title: {roadmap['roadmap_title']}\n"
                    context += "\nRoadmap Steps:\n"
                    for step in steps_result.data:
                        context += f"Week {step['week_no']}: {step['topic']} (Status: {step['status']})\n"
                        context += f"  - {step['description']}\n"
                        context += f"  - Milestone: {step['milestone']}\n"

        # Generate AI response
        if not genai_available or not model:
            reply = "I'm currently unavailable. Please try again later or contact your career counselor for guidance."
        else:
            try:
                prompt = f"""
You are a friendly and knowledgeable career mentor helping a student with their career journey.

{context}

Student's Question: {message}

Provide a helpful, encouraging, and practical response. If the student asks about a specific topic from their roadmap:
1. Explain the concept in simple, step-by-step terms
2. Provide practical examples
3. Suggest exercises or mini-projects they can try
4. Encourage them and acknowledge their progress

Keep your response concise (3-5 paragraphs), actionable, and motivating.
Use plain text format (no markdown).
"""

                response = model.generate_content(prompt)
                reply = response.text.strip()

            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                reply = "I encountered an error processing your question. Please try rephrasing or ask something else."

        # Store the chat message in database
        chat_result = supabase.table('mentor_sessions').insert({
            'student_id': actual_student_id,
            'roadmap_id': roadmap_id,
            'message': message,
            'reply': reply
        }).execute()

        if not chat_result.data:
            logger.warning("Failed to store chat message in database")

        return jsonify({
            'success': True,
            'reply': reply,
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error in mentor chat: {e}")
        return jsonify({'error': str(e)}), 500


@career_roadmap_bp.route('/mentor/history/<student_id>', methods=['GET'])
def get_mentor_history(student_id):
    """
    GET /api/roadmap/mentor/history/<student_id>
    Get chat history for a student
    """
    try:
        roadmap_id = request.args.get('roadmap_id')

        query = supabase.table('mentor_sessions')\
            .select('*')\
            .eq('student_id', student_id)\
            .order('created_at', desc=True)

        if roadmap_id:
            query = query.eq('roadmap_id', roadmap_id)

        result = query.limit(50).execute()

        return jsonify({
            'success': True,
            'history': result.data if result.data else []
        }), 200

    except Exception as e:
        logger.error(f"Error fetching mentor history: {e}")
        return jsonify({'error': str(e)}), 500

