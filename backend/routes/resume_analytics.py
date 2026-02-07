from flask import Blueprint, request, jsonify, make_response
from supabase_client import get_supabase
from datetime import datetime
from functools import wraps
import os
import uuid
from werkzeug.utils import secure_filename
import hashlib
import traceback

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
    """Upload and analyze student resume with enhanced error handling and logging"""
    # Initialize file_path in the outer scope for cleanup in case of errors
    file_path = None
    
    try:
        import sys, traceback
        from werkzeug.utils import secure_filename
        
        # Detailed request logging
        print("\n" + "="*80)
        print("[DEBUG] Resume upload request received")
        print(f"[DEBUG] Python version: {sys.version}")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        print(f"[DEBUG] Request method: {request.method}")
        print(f"[DEBUG] Content-Type: {request.headers.get('Content-Type')}")
        print(f"[DEBUG] Content-Length: {request.headers.get('Content-Length')}")
        print(f"[DEBUG] Form data: {dict(request.form)}")
        print(f"[DEBUG] Files: {[f.filename for f in request.files.getlist('file')] if 'file' in request.files else 'No files'}")
        print("="*80 + "\n")
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = make_response()
            return add_cors_headers(response)
        
        # Validate request content type for file upload
        if 'multipart/form-data' not in request.headers.get('Content-Type', ''):
            return jsonify({
                "success": False,
                "error": "Invalid content type. Expected 'multipart/form-data'"
            }), 400
        
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
        
        # Validate student_id format
        try:
            # Check if student_id is a valid UUID or integer
            try:
                uuid.UUID(str(student_id))
            except ValueError:
                # Not a UUID, check if it's an integer
                if not str(student_id).isdigit():
                    raise ValueError("Student ID must be a valid UUID or integer")
        except Exception as e:
            print(f"[ERROR] Invalid student_id format: {student_id}")
            return jsonify({
                "success": False,
                "error": "Invalid Student ID format. Must be a valid UUID or integer"
            }), 400
        
        print(f"[DEBUG] Processing resume upload for student_id: {student_id}")
        
        # Verify student exists
        try:
            student_result = supabase.from_('students')\
                .select('id, full_name, register_number, email')\
                .eq('id', student_id)\
                .execute()
            
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
            error_msg = f"Error checking student existence: {str(e)}"
            print(f"[EXCEPTION] {error_msg}")
            print(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": "Error verifying student information",
                "details": str(e)
            }), 500
        
        # Validate file upload
        if 'file' not in request.files:
            print("[ERROR] No file part in the request")
            print(f"[DEBUG] Available files: {list(request.files.keys())}")
            return jsonify({
                "success": False, 
                "error": "No file part in the request"
            }), 400
        
        file = request.files['file']
        
        # Validate file object
        if not file or file.filename == '':
            print("[ERROR] No file selected or empty filename")
            return jsonify({
                "success": False, 
                "error": "No file selected"
            }), 400
        
        print(f"[DEBUG] Processing file: {file.filename} (Type: {file.content_type}, Size: {file.content_length or 0} bytes)")
        
        # Validate file type
        if not allowed_file(file.filename):
            print(f"[ERROR] Invalid file type: {file.filename}")
            return jsonify({
                "success": False, 
                "error": "Invalid file type. Only PDF, DOC, DOCX, or TXT files are allowed.",
                "allowed_extensions": ["pdf", "doc", "docx", "txt"]
            }), 400
        
        # Sanitize filename
        filename = secure_filename(file.filename)
        if not filename:
            raise ValueError("Invalid filename after sanitization")
        
        print(f"[DEBUG] Sanitized filename: {filename}")
        
        # Set up upload directory
        try:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            upload_dir = os.path.join(backend_dir, 'uploads', 'resumes')
            
            # Ensure upload directory exists and is writable
            os.makedirs(upload_dir, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(upload_dir, f'.test_{os.getpid()}')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                raise Exception(f"Cannot write to upload directory '{upload_dir}': {str(e)}")
            
        except Exception as e:
            error_msg = f"Error setting up upload directory: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": "Server configuration error",
                "details": error_msg
            }), 500
        
        # Generate unique filename with timestamp for better traceability
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{student_id}_{timestamp}_{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        print(f"[DEBUG] Saving file to: {file_path}")
        
        try:
            # Ensure we're at the start of the file
            if hasattr(file, 'seek'):
                file.seek(0)
            
            # Save the file in chunks to handle large files
            chunk_size = 4096  # 4KB chunks
            
            try:
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = file.stream.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                
                # Verify the file was saved
                if not os.path.exists(file_path):
                    raise Exception("File was not saved correctly")
                
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    raise Exception("Uploaded file is empty")
                
                # Set reasonable file size limit (e.g., 10MB)
                max_file_size = 10 * 1024 * 1024  # 10MB
                if file_size > max_file_size:
                    raise Exception(f"File size ({file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)")
                
                print(f"[DEBUG] File saved successfully: {file_path} ({file_size} bytes)")
                
            except IOError as e:
                raise Exception(f"I/O error while saving file: {str(e)}")
            except Exception as e:
                raise Exception(f"Unexpected error saving file: {str(e)}")
                
        except Exception as e:
            error_msg = f"Error saving file: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(traceback.format_exc())

            # Clean up if file was partially saved
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"[DEBUG] Cleaned up partially uploaded file: {file_path}")
                except Exception as cleanup_error:
                    print(f"[ERROR] Failed to clean up file {file_path}: {str(cleanup_error)}")

            return jsonify({
                "success": False,
                "error": "Failed to save uploaded file",
                "details": error_msg,
                "max_file_size": "10MB",
                "allowed_formats": ["pdf", "doc", "docx", "txt"]
            }), 500

        # For demo purposes, create mock analysis
        try:
            # Read the actual file content for analysis
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()

            # If the file is empty or we couldn't read text content, use a fallback
            if not file_content.strip():
                print("[WARNING] File appears to be empty or could not be read as text")
                file_content = f"""
                {student.get('full_name', 'Student')}
                Student ID: {student.get('register_number', 'N/A')}
                Email: {student.get('email', 'N/A')}

                [Resume content could not be extracted or file is in binary format]
                """

            # Analyze the resume content
            analysis = analyze_resume_content(file_content)

            # Add file metadata to analysis
            analysis['file_metadata'] = {
                'original_name': filename,
                'stored_name': unique_filename,
                'size_bytes': os.path.getsize(file_path),
                'content_type': file.content_type,
                'upload_timestamp': datetime.utcnow().isoformat() + 'Z',  # ISO 8601 with UTC
                'checksum': hashlib.md5(open(file_path, 'rb').read()).hexdigest()
            }

            # Prepare resume data for database
            resume_data = {
                'student_id': student_id,
                'file_name': unique_filename,
                'file_path': file_path,  # Store full server path
                'file_url': f"/api/resumes/{unique_filename}",  # URL path for client access
                'file_size': os.path.getsize(file_path),
                'file_type': file.content_type,
                'upload_date': datetime.utcnow().isoformat() + 'Z',
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'is_active': True,
                'version': 1,
                'metadata': {
                    'original_name': filename,
                    'analysis': analysis,
                    'status': 'processed'
                }
            }

        except Exception as e:
            error_msg = f"Error processing file content: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(traceback.format_exc())

            # Prepare error response with partial data
            resume_data = {
                'student_id': student_id,
                'file_name': unique_filename,
                'file_path': file_path,
                'file_url': f"/api/resumes/{unique_filename}",
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'file_type': file.content_type,
                'upload_date': datetime.utcnow().isoformat() + 'Z',
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'is_active': False,
                'version': 1,
                'metadata': {
                    'original_name': filename,
                    'error': error_msg,
                    'status': 'error'
                }
            }

            # Don't fail the entire upload, just record the error
            analysis = {
                'error': 'File was uploaded but could not be processed',
                'details': error_msg,
                'file_metadata': {
                    'original_name': filename,
                    'stored_name': unique_filename,
                    'size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'content_type': file.content_type,
                    'upload_timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }

        # Database operation with transaction support and retry logic
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                # Begin transaction (if supported by your database)
                # This depends on your Supabase/PostgreSQL configuration

                # Verify student exists (double-check)
                verify_student = supabase.from_('students')\
                    .select('id, full_name, email')\
                    .eq('id', student_id)\
                    .execute()

                if not verify_student.data:
                    raise Exception(f"Student with ID {student_id} not found during final verification")

                # Check if a resume already exists for this student
                existing_resume = supabase.from_('resumes')\
                    .select('id, version')\
                    .eq('student_id', student_id)\
                    .eq('is_active', True)\
                    .execute()

                # If an active resume exists, mark it as inactive
                if existing_resume.data:
                    old_version = existing_resume.data[0].get('version', 1)
                    resume_data['version'] = old_version + 1

                    # Update existing record to inactive
                    supabase.from_('resumes')\
                        .update({'is_active': False, 'last_updated': datetime.utcnow().isoformat() + 'Z'})\
                        .eq('student_id', student_id)\
                        .eq('is_active', True)\
                        .execute()

                # Insert new resume record
                result = supabase.from_('resumes')\
                    .insert(resume_data)\
                    .execute()

                if hasattr(result, 'error') and result.error:
                    error_msg = str(result.error)
                    if "violates foreign key constraint" in error_msg.lower():
                        raise Exception("Invalid student reference - student does not exist")
                    raise Exception(f"Database error: {error_msg}")

                # If we get here, the transaction was successful
                break

            except Exception as e:
                error_msg = str(e)
                print(f"[EXCEPTION] Attempt {attempt + 1}/{max_retries} - Database operation failed: {error_msg}")
                print(traceback.format_exc())

                if attempt == max_retries - 1:  # Last attempt failed
                    # Try to clean up the uploaded file since we couldn't save to DB
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"[DEBUG] Cleaned up uploaded file after database error: {file_path}")
                        except Exception as cleanup_error:
                            print(f"[ERROR] Failed to clean up file after database error: {str(cleanup_error)}")

                    return jsonify({
                        "success": False,
                        "error": "Failed to save resume information to database",
                        "details": error_msg,
                        "attempts": attempt + 1
                    }), 500

                # Wait before retrying
                import time
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

        # Prepare success response with all relevant information
        response_data = {
            "success": True,
            "message": "Resume uploaded and analyzed successfully",
            "data": {
                "resume_id": str(uuid.uuid4()),  # This should ideally come from the database
                "student_id": student_id,
                "file_url": f"/api/resumes/{unique_filename}",
                "resume_url": f"/api/resumes/{unique_filename}",
                "download_url": f"/api/resumes/{unique_filename}/download",
                "analysis": analysis,
                "metadata": {
                    "filename": unique_filename,
                    "original_name": filename,
                    "file_size": os.path.getsize(file_path),
                    "content_type": file.content_type,
                    "upload_timestamp": datetime.utcnow().isoformat() + 'Z',
                    "version": resume_data.get('version', 1)
                },
                "student_info": {
                    "full_name": student.get('full_name'),
                    "register_number": student.get('register_number'),
                    "email": student.get('email')
                }
            },
            "timestamps": {
                "server_time": datetime.utcnow().isoformat() + 'Z',
                "timezone": "UTC"
            }
        }

        print(f"[SUCCESS] Resume uploaded successfully for student {student_id}")
        print(f"[DEBUG] Response data: {response_data}")

        return jsonify(response_data)
    except Exception as e:
        import traceback
        error_msg = f"Unexpected error in upload_resume: {str(e)}"
        print(f"[CRITICAL] {error_msg}")
        print(traceback.format_exc())
        
        # Log the full error with stack trace to a file for debugging
        try:
            error_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                        'logs', 'resume_upload_errors.log')
            os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
            with open(error_log_path, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"[{datetime.utcnow().isoformat()}] ERROR: {error_msg}\n")
                f.write(f"Student ID: {student_id if 'student_id' in locals() else 'N/A'}\n")
                f.write(f"File: {file.filename if 'file' in locals() and file else 'N/A'}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
        except Exception as log_error:
            print(f"[ERROR] Failed to write to error log: {str(log_error)}")
        
        # Clean up any partially uploaded files
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[DEBUG] Cleaned up file after error: {file_path}")
            except Exception as cleanup_error:
                print(f"[ERROR] Failed to clean up file {file_path}: {str(cleanup_error)}")
        
        # Return a user-friendly error message with a unique error ID for support
        error_id = str(uuid.uuid4())[:8]
        print(f"[ERROR] Error ID: {error_id}")
        
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred while processing your request",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "support_contact": "support@example.com"
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
    
@resume_analytics_bp.route('/analysis/<student_id>', methods=['PUT', 'OPTIONS'])
@handle_errors
def update_resume_analysis(student_id):
    """Update resume analysis for a specific student"""
    try:
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = make_response()
            return add_cors_headers(response)
        
        # Get the analysis data from request
        analysis_data = request.get_json()
        if not analysis_data or 'analysis' not in analysis_data:
            return jsonify({
                "success": False,
                "error": "Analysis data is required"
            }), 400
        
        analysis = analysis_data['analysis']
        
        # Validate required fields
        required_fields = ['score', 'strengths', 'skills_identified', 'recommendations']
        for field in required_fields:
            if field not in analysis:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        print(f"[DEBUG] Updating analysis for student {student_id}")
        
        # Find the latest active resume for this student
        existing_resume = supabase.from_('resumes')\
            .select('id, metadata')\
            .eq('student_id', student_id)\
            .eq('is_active', True)\
            .execute()
        
        if not existing_resume.data:
            return jsonify({
                "success": False,
                "error": "No active resume found for this student"
            }), 404
        
        resume_id = existing_resume.data[0]['id']
        current_metadata = existing_resume.data[0]['metadata'] or {}
        
        # Update the metadata with new analysis
        updated_metadata = {
            **current_metadata,
            'analysis': analysis
        }
        
        # Update the resume record
        update_result = supabase.from_('resumes')\
            .update({
                'metadata': updated_metadata,
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            })\
            .eq('id', resume_id)\
            .execute()
        
        if hasattr(update_result, 'error') and update_result.error:
            return jsonify({
                "success": False,
                "error": f"Failed to update analysis: {str(update_result.error)}"
            }), 500
        
        return jsonify({
            "success": True,
            "message": "Resume analysis updated successfully",
            "data": {
                "resume_id": resume_id,
                "analysis": analysis
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to update resume analysis: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to update resume analysis",
            "details": str(e)
        }), 500
