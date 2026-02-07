from flask import Blueprint, request, jsonify, make_response
from supabase_client import get_supabase
from datetime import datetime
from functools import wraps
import os
import uuid
from werkzeug.utils import secure_filename

# CORS headers
def add_cors_headers(response):
    # Always echo back the origin header when credentials are used
    origin = request.headers.get('Origin', '')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'  # Default development frontend
        
    # Allow credentials
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Common headers needed for file uploads and JSON
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, POST, DELETE, OPTIONS'
    
    # Cache preflight response for 1 hour
    response.headers['Access-Control-Max-Age'] = '3600'
    
    # Ensure the response has a Content-Type header for OPTIONS requests
    if request.method == 'OPTIONS' and 'Content-Type' not in response.headers:
        response.headers['Content-Type'] = 'text/plain'
        
    return response

resume_analytics_bp = Blueprint('resume_analytics', __name__)

# Initialize Supabase client
supabase = get_supabase()

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Handle preflight requests first
            if request.method == 'OPTIONS':
                response = make_response()
                return add_cors_headers(response)
            
            # Execute the function and get the response
            result = f(*args, **kwargs)
            
            # Convert dictionary responses to JSON responses
            if isinstance(result, tuple):
                if len(result) == 2 and isinstance(result[1], int):
                    # Handle (response, status_code) pattern
                    response = make_response(jsonify(result[0]) if isinstance(result[0], dict) else result[0], result[1])
                else:
                    # Handle other tuple responses
                    response = make_response(jsonify({"data": result}))
            elif isinstance(result, dict):
                response = make_response(jsonify(result))
            else:
                response = make_response(result)
                
            # Add CORS headers to the response
            return add_cors_headers(response)
                
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            error_response = make_response(jsonify({
                "success": False,
                "error": "An error occurred while processing your request"
            }), 500)
            # Log detailed error information
            print(f"Exception type: {type(e)}")
            print(f"Request method: {request.method}")
            print(f"Request headers: {dict(request.headers)}")
            print(f"Request form: {dict(request.form)}")
            print(f"Request files: {request.files}")
            
            # Create error response
            error_response = make_response(jsonify({
                "success": False, 
                "error": str(e),
                "debug_info": {
                    "exception_type": str(type(e)),
                    "request_method": request.method,
                    "content_type": request.headers.get('Content-Type')
                }
            }), 500)
            return add_cors_headers(error_response)
    return wrapper

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'txt'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def analyze_resume_content(text_content):
    """
    Analyze resume content and provide insights
    This is a simplified version that works without external AI APIs
    """
    analysis = {
        "skills_identified": [],
        "experience_level": "Entry Level",
        "education_level": "Bachelor's",
        "strengths": [],
        "recommendations": [],
        "score": 0
    }
    
    # Simple keyword-based analysis
    text_lower = text_content.lower()
    
    # Technical skills detection
    technical_skills = [
        "python", "java", "javascript", "react", "node.js", "sql", "mongodb",
        "machine learning", "data science", "artificial intelligence", "web development",
        "mobile development", "cloud computing", "aws", "azure", "docker", "kubernetes"
    ]
    
    for skill in technical_skills:
        if skill in text_lower:
            analysis["skills_identified"].append(skill.title())
    
    # Experience level detection
    if any(word in text_lower for word in ["senior", "lead", "manager", "architect"]):
        analysis["experience_level"] = "Senior Level"
    elif any(word in text_lower for word in ["junior", "associate", "intern"]):
        analysis["experience_level"] = "Junior Level"
    elif any(word in text_lower for word in ["years", "experience", "worked"]):
        analysis["experience_level"] = "Mid Level"
    
    # Education level detection
    if any(word in text_lower for word in ["phd", "doctorate", "ph.d"]):
        analysis["education_level"] = "Doctorate"
    elif any(word in text_lower for word in ["master", "mtech", "mba", "ms"]):
        analysis["education_level"] = "Master's"
    elif any(word in text_lower for word in ["bachelor", "btech", "be", "bs"]):
        analysis["education_level"] = "Bachelor's"
    
    # Generate strengths based on content
    if len(analysis["skills_identified"]) > 5:
        analysis["strengths"].append("Strong technical skill set")
    if "project" in text_lower:
        analysis["strengths"].append("Project experience")
    if any(word in text_lower for word in ["leadership", "team", "managed"]):
        analysis["strengths"].append("Leadership qualities")
    if any(word in text_lower for word in ["certification", "certified"]):
        analysis["strengths"].append("Professional certifications")
    
    # Generate recommendations
    if len(analysis["skills_identified"]) < 3:
        analysis["recommendations"].append("Consider adding more technical skills")
    if "github" not in text_lower:
        analysis["recommendations"].append("Include GitHub profile to showcase projects")
    if "linkedin" not in text_lower:
        analysis["recommendations"].append("Add LinkedIn profile for professional networking")
    if len(analysis["strengths"]) < 2:
        analysis["recommendations"].append("Highlight more achievements and experiences")
    
    # Calculate score (0-100)
    score = 0
    score += min(len(analysis["skills_identified"]) * 10, 40)  # Max 40 for skills
    score += len(analysis["strengths"]) * 15  # 15 points per strength
    score += 20 if analysis["experience_level"] != "Entry Level" else 10  # Experience bonus
    score += 10 if analysis["education_level"] in ["Master's", "Doctorate"] else 5  # Education bonus
    
    analysis["score"] = min(score, 100)
    
    return analysis

@resume_analytics_bp.route('/upload', methods=['POST', 'OPTIONS'])
@handle_errors
def upload_resume():
    """Upload and analyze student resume"""
    try:
        # Print full request details for debugging
        print("\n[DEBUG] Resume upload request received")
        print(f"[DEBUG] Request method: {request.method}")
        print(f"[DEBUG] Request headers: {dict(request.headers)}")
        print(f"[DEBUG] Request form data: {dict(request.form)}")
        print(f"[DEBUG] Request files: {request.files}")
        print(f"[DEBUG] Request environ: {request.environ.get('wsgi.input_terminated', 'Not found')}")
        
        # Handle preflight requests explicitly
        if request.method == 'OPTIONS':
            response = make_response()
            response = add_cors_headers(response)
            return response
            
        # Get student_id from form data
        student_id = request.form.get('student_id')
        if not student_id:
            print("[ERROR] No student_id provided in form data")
            return jsonify({
                "success": False, 
                "error": "Student ID is required",
                "debug_info": {
                    "form_data": dict(request.form),
                    "content_type": request.headers.get('Content-Type')
                }
            }), 400
            
        print(f"[DEBUG] Processing resume upload for student_id: {student_id}")
            
        # Check if student exists with more detailed error handling
        try:
            student_result = supabase.from_('students').select('id, full_name, register_number').eq('id', student_id).execute()
            
            # Check for errors in the response
            if hasattr(student_result, 'error') and student_result.error:
                print(f"[ERROR] Database error when fetching student: {student_result.error}")
                return jsonify({
                    "success": False, 
                    "error": "Database error when verifying student",
                    "details": str(student_result.error)
                }), 500
                
            if not student_result.data:
                print(f"[ERROR] Student not found with ID: {student_id}")
                return jsonify({
                    "success": False, 
                    "error": f"Student with ID {student_id} not found in the system"
                }), 404
            
            student = student_result.data[0]
            print(f"[DEBUG] Found student: {student}")
            
        except Exception as e:
            print(f"[EXCEPTION] Error checking student existence: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Error verifying student information",
                "details": str(e)
            }), 500
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            print("[ERROR] No file in request.files")
            print(f"[DEBUG] Available files: {list(request.files.keys())}")
            return jsonify({"success": False, "error": "No file part"}), 400
            
        file = request.files['file']
        print(f"[DEBUG] File received: {file.filename}")
        
        if file.filename == '':
            print("[ERROR] Empty filename")
            return jsonify({"success": False, "error": "No selected file"}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            try:
                # Create uploads directory if it doesn't exist
                backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                upload_folder = os.path.join(backend_dir, 'uploads', 'resumes')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Generate unique filename
                unique_filename = f"{student_id}_{uuid.uuid4().hex[:8]}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                
                print(f"Saving file to: {file_path}")
                # Save the file
                file.save(file_path)
            except Exception as e:
                print(f"Error saving file: {str(e)}")
                return jsonify({"success": False, "error": f"Error saving file: {str(e)}"}), 500
            
            # For demo purposes, create mock analysis
            mock_resume_text = f"""
            {student.get('full_name', 'Student')}
            Student ID: {student.get('register_number', 'N/A')}
            
            Education:
            Bachelor of Technology in Computer Science Engineering
            
            Skills:
            Python, Java, JavaScript, React, Node.js, SQL, MongoDB
            Machine Learning, Data Science, Web Development
            
            Projects:
            1. Student Management System - Full stack web application
            2. E-commerce Website - React and Node.js based platform
            3. Data Analysis Project - Python and Machine Learning
            
            Experience:
            Intern at Tech Company (6 months)
            Freelance Web Developer (1 year)
            
            Certifications:
            AWS Cloud Practitioner
            Python Programming Certification
            """
            
            # Analyze the resume content
            analysis = analyze_resume_content(mock_resume_text)
            
            # Store resume information in database
            resume_data = {
                'student_id': student_id,
                'file_name': unique_filename,
                'original_name': filename,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'file_type': file.content_type,
                'analysis': analysis,
                'uploaded_at': datetime.now().isoformat()
            }
            
            try:
                # First, verify the student exists again right before insertion (double-check)
                verify_student = supabase.from_('students').select('id').eq('id', student_id).execute()
                
                if not verify_student.data:
                    return jsonify({
                        "success": False,
                        "error": "Student record not found during final verification",
                        "details": f"Student ID {student_id} was not found in the database"
                    }), 404
                
                # Insert or update resume record in the database
                result = supabase.from_('student_resumes').upsert({
                    'student_id': student_id,
                    **resume_data
                }).execute()
                
                if hasattr(result, 'error') and result.error:
                    error_msg = str(result.error)
                    if "violates foreign key constraint" in error_msg.lower():
                        return jsonify({
                            "success": False,
                            "error": "Invalid student reference",
                            "details": "The provided student ID does not exist in the system"
                        }), 400
                    return jsonify({
                        "success": False,
                        "error": "Database error",
                        "details": error_msg
                    }), 500
                    
            except Exception as e:
                error_msg = str(e)
                print(f"[EXCEPTION] Error during database operation: {error_msg}")
                return jsonify({
                    "success": False,
                    "error": "Failed to save resume information",
                    "details": error_msg
                }), 500
            
            return jsonify({
                "success": True,
                "message": "Resume uploaded and analyzed successfully",
                "data": {
                    "resume_url": f"/uploads/resumes/{unique_filename}",
                    "analysis": analysis,
                    "upload_info": {
                        "filename": unique_filename,
                        "original_name": filename,
                        "upload_date": datetime.now().isoformat()
                    }
                }
            })
        
        return jsonify({
            "success": False, 
            "error": "Invalid file type. Please upload PDF, DOC, DOCX, or TXT files only."
        }), 400
    except Exception as e:
        print(f"Error in upload_resume: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An error occurred while processing your request"
        }), 500

@resume_analytics_bp.route('/<student_id>', methods=['GET', 'OPTIONS'])
def get_resume(student_id):
    """Get student's resume by ID (accepts both UUID and integer)"""
    try:
        # Handle preflight request
        if request.method == 'OPTIONS':
            response = make_response()
            return add_cors_headers(response)

        print(f"Fetching resume for student: {student_id}")

        # Handle both user_id (UUID from Supabase auth) and student id (integer or UUID)
        # First, try to find the actual student record
        actual_student_id = None
        try:
            # Try to find by user_id first (UUID from Supabase auth)
            student_result = supabase.table('students').select('id, user_id').eq('user_id', student_id).execute()
            if student_result.data:
                actual_student_id = student_result.data[0]['id']
                print(f"Found student by user_id: {actual_student_id}")
            else:
                # Try by id directly
                student_result = supabase.table('students').select('id, user_id').eq('id', student_id).execute()
                if student_result.data:
                    actual_student_id = student_result.data[0]['id']
                    print(f"Found student by id: {actual_student_id}")
        except Exception as e:
            print(f"Error looking up student: {e}")

        # Use the actual student_id if found, otherwise use the provided one
        search_id = actual_student_id if actual_student_id else student_id

        # First, attempt to fetch from the primary 'resumes' table.
        # If the table does not exist or returns no results, fall back to 'student_resumes' which
        # some parts of the codebase use. This makes the endpoint tolerant to schema differences.
        try:
            try:
                print("Attempting to query 'resumes' table")
                response = supabase.table('resumes') \
                    .select('*') \
                    .eq('student_id', search_id) \
                    .execute()

                if response and getattr(response, 'data', None):
                    print(f"Found resume in 'resumes' table for student {search_id}")
                    result = {"success": True, "data": response.data[0]}
                    response = make_response(jsonify(result))
                    return add_cors_headers(response)
                else:
                    print(f"No resume found in 'resumes' table for {search_id}, falling back to 'student_resumes'")
            except Exception as table_error:
                print(f"Error accessing 'resumes' table: {str(table_error)}")

            # Fallback: try 'student_resumes' table
            try:
                fallback_resp = supabase.table('student_resumes') \
                    .select('*') \
                    .eq('student_id', search_id) \
                    .execute()

                if fallback_resp and getattr(fallback_resp, 'data', None):
                    print(f"Found resume in 'student_resumes' table for student {search_id}")
                    result = {"success": True, "data": fallback_resp.data[0]}
                    response = make_response(jsonify(result))
                    return add_cors_headers(response)
                else:
                    print(f"No resume found in either 'resumes' or 'student_resumes' for {search_id}")
                    result = {"success": False, "error": "Resume not found"}
                    response = make_response(jsonify(result), 404)
                    return add_cors_headers(response)

            except Exception as fallback_error:
                print(f"Error querying fallback 'student_resumes' table: {str(fallback_error)}")
                error_response = make_response(jsonify({
                    "success": False,
                    "error": "Database error when querying resume tables",
                    "details": str(fallback_error)
                }), 500)
                return add_cors_headers(error_response)

        except Exception as query_error:
            print(f"Unexpected error when fetching resume: {str(query_error)}")
            error_response = make_response(jsonify({
                "success": False,
                "error": "Failed to fetch resume",
                "details": str(query_error)
            }), 500)
            return add_cors_headers(error_response)

    except Exception as e:
        print(f"Unexpected error in get_resume: {str(e)}")
        error_response = make_response(jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500)
        return add_cors_headers(error_response)

@resume_analytics_bp.route('/student/<int:student_id>/resume/analysis', methods=['GET'])
@handle_errors
def get_resume_analysis(student_id):
    """Get resume analysis for a student"""
    # Check if student exists
    student_result = supabase.table('students').select('id, full_name, register_number').eq('id', student_id).execute()
    if not student_result.data:
        return jsonify({"success": False, "error": "Student not found"}), 404
    
    student = student_result.data[0]
    
    # For demo purposes, return mock analysis
    # In a real application, you would fetch this from the database
    mock_analysis = {
        "skills_identified": [
            "Python", "Java", "JavaScript", "React", "Node.js", 
            "SQL", "MongoDB", "Machine Learning", "Data Science", "Web Development"
        ],
        "experience_level": "Junior Level",
        "education_level": "Bachelor's",
        "strengths": [
            "Strong technical skill set",
            "Project experience",
            "Professional certifications"
        ],
        "recommendations": [
            "Include GitHub profile to showcase projects",
            "Add more leadership experiences",
            "Consider contributing to open source projects"
        ],
        "score": 78,
        "last_updated": datetime.now().isoformat()
    }
    
    return jsonify({
        "success": True,
        "data": {
            "student_info": student,
            "resume_analysis": mock_analysis,
            "analysis_date": datetime.now().isoformat()
        }
    })

@resume_analytics_bp.route('/student/<int:student_id>/resume/recommendations', methods=['GET'])
@handle_errors
def get_resume_recommendations(student_id):
    """Get personalized recommendations for resume improvement"""
    # Check if student exists
    student_result = supabase.table('students').select('*').eq('id', student_id).execute()
    if not student_result.data:
        return jsonify({"success": False, "error": "Student not found"}), 404
    
    student = student_result.data[0]
    
    # Generate course-specific recommendations
    course_specific_recommendations = {
        1: {  # CSE
            "technical_skills": ["Python", "Java", "Data Structures", "Algorithms", "System Design"],
            "projects": ["Web Applications", "Mobile Apps", "Machine Learning Projects"],
            "certifications": ["AWS Cloud Practitioner", "Google Cloud Associate", "Microsoft Azure Fundamentals"]
        },
        2: {  # ECE
            "technical_skills": ["MATLAB", "Verilog", "VLSI Design", "Signal Processing", "Embedded Systems"],
            "projects": ["IoT Projects", "Signal Processing Applications", "Hardware Design"],
            "certifications": ["Embedded Systems Certification", "IoT Certification"]
        }
    }
    
    course_id = student.get('course_id', 1)
    recommendations = course_specific_recommendations.get(course_id, course_specific_recommendations[1])
    
    personalized_recommendations = {
        "technical_skills_to_add": recommendations["technical_skills"],
        "project_suggestions": recommendations["projects"],
        "certification_recommendations": recommendations["certifications"],
        "general_tips": [
            "Use action verbs to describe your experiences",
            "Quantify your achievements with numbers and metrics",
            "Keep your resume to 1-2 pages maximum",
            "Use a clean, professional format",
            "Proofread for grammar and spelling errors"
        ],
        "industry_trends": [
            "Cloud computing skills are in high demand",
            "AI and Machine Learning expertise is valuable",
            "Full-stack development skills are sought after",
            "DevOps and automation skills are important"
        ]
    }
    
    return jsonify({
        "success": True,
        "data": {
            "student_info": {
                "name": student['full_name'],
                "course": "Computer Science Engineering",  # You can fetch this from courses table
                "semester": student.get('current_semester', 1)
            },
            "recommendations": personalized_recommendations,
            "generated_date": datetime.now().isoformat()
        }
    })

@resume_analytics_bp.route('/resume/analytics/dashboard', methods=['GET'])
@handle_errors
def get_resume_analytics_dashboard():
    """Get overall resume analytics for admin dashboard"""
    # Mock data for demonstration
    # In a real application, you would calculate these from the database
    
    dashboard_data = {
        "total_resumes_uploaded": 45,
        "average_score": 72.5,
        "skill_distribution": {
            "Python": 35,
            "Java": 28,
            "JavaScript": 32,
            "React": 25,
            "Node.js": 20,
            "SQL": 30,
            "Machine Learning": 15
        },
        "experience_level_distribution": {
            "Entry Level": 25,
            "Junior Level": 15,
            "Mid Level": 5,
            "Senior Level": 0
        },
        "education_level_distribution": {
            "Bachelor's": 40,
            "Master's": 5,
            "Doctorate": 0
        },
        "top_recommendations": [
            "Include GitHub profile to showcase projects",
            "Add more technical skills",
            "Highlight leadership experiences",
            "Include professional certifications"
        ],
        "recent_uploads": [
            {"student_name": "Rahul Verma", "score": 78, "upload_date": "2025-08-10"},
            {"student_name": "Priya Singh", "score": 82, "upload_date": "2025-08-09"},
            {"student_name": "Amit Kumar", "score": 65, "upload_date": "2025-08-08"}
        ]
    }
    
    return jsonify({
        "success": True,
        "data": dashboard_data,
        "generated_at": datetime.now().isoformat()
    })

