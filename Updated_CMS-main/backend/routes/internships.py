
import os
import time
import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, jsonify, request, make_response
from bs4 import BeautifulSoup  # type: ignore[reportMissingImports]
from supabase import create_client
import concurrent.futures
import sys

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import get_supabase

# Initialize Flask Blueprint and Supabase client
bp = Blueprint('internships', __name__)
supabase = get_supabase()

# Table names
INTERNSHIPS_TABLE = 'internships'

# Error messages
INTERNAL_SERVER_ERROR = "An error occurred while processing your request"

def add_cors_headers(response):
    """Add CORS headers to the response"""
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

def _parse_stipend(stipend_str: str) -> Dict[str, Any]:
    """Parse stipend string into min, max, and is_unpaid"""
    if not stipend_str:
        return {'min': 0, 'max': 0, 'is_unpaid': True}
        
    try:
        # Remove any non-numeric characters except comma and period
        clean_str = re.sub(r'[^\d.,]', '', stipend_str)
        
        # Handle ranges like "1000-2000"
        if '-' in clean_str:
            min_val, max_val = clean_str.split('-')
            return {
                'min': float(min_val.replace(',', '')),
                'max': float(max_val.replace(',', '')),
                'is_unpaid': False
            }
        # Handle single values
        elif clean_str:
            val = float(clean_str.replace(',', ''))
            return {'min': val, 'max': val, 'is_unpaid': False}
            
    except (ValueError, AttributeError) as e:
        print(f"Error parsing stipend '{stipend_str}': {str(e)}")
        
    return {'min': 0, 'max': 0, 'is_unpaid': True}

def _parse_duration(duration_str: str) -> str:
    """Parse and standardize duration string"""
    if not duration_str:
        return 'Not specified'
        
    duration_str = duration_str.lower()
    
    # Common duration patterns
    patterns = {
        r'\b(1|one)\s*month\b': '1 month',
        r'\b(2|two)\s*months?\b': '2 months',
        r'\b(3|three)\s*months?\b': '3 months',
        r'\b(4|four)\s*months?\b': '4 months',
        r'\b(5|five)\s*months?\b': '5 months',
        r'\b(6|six)\s*months?\b': '6 months',
        r'\b(1|one)\s*year\b': '1 year',
        r'\b(2|two)\s*years?\b': '2 years',
        r'\bfull[-\s]?time\b': 'Full-time',
        r'\bpart[-\s]?time\b': 'Part-time',
        r'\bflexible\b': 'Flexible',
        r'\bnot specified\b': 'Not specified'
    }
    
    for pattern, replacement in patterns.items():
        if re.search(pattern, duration_str):
            return replacement
            
    return duration_str.capitalize()

def _parse_posted_date(posted_str: str) -> Optional[datetime]:
    """Parse posted date string into datetime"""
    if not posted_str:
        return None
        
    try:
        # Handle relative dates like "2 days ago"
        if 'day' in posted_str.lower():
            days_ago = int(re.search(r'\d+', posted_str).group(0))
            return datetime.utcnow() - timedelta(days=days_ago)
            
        # Handle absolute dates (add more formats as needed)
        date_formats = [
            '%Y-%m-%d',  # 2023-01-01
            '%d-%m-%Y',  # 01-01-2023
            '%m/%d/%Y',  # 01/01/2023
            '%d %b %Y',  # 01 Jan 2023
            '%b %d, %Y'  # Jan 01, 2023
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(posted_str, fmt)
            except ValueError:
                continue
                
    except Exception as e:
        print(f"Error parsing date '{posted_str}': {str(e)}")
        
    return None

def _save_internship_opportunity(internship_data: dict) -> Optional[dict]:
    """Save an internship opportunity to the database"""
    try:
        # Ensure required fields have default values
        internship_data['title'] = internship_data.get('title', 'Internship Position')
        internship_data['company'] = internship_data.get('company', 'Company')
        internship_data['location'] = internship_data.get('location', 'Remote')
        internship_data['is_remote'] = internship_data.get('is_remote', False)
        internship_data['is_active'] = internship_data.get('is_active', True)
        internship_data['posted_date'] = internship_data.get('posted_date', datetime.utcnow().isoformat())
        
        # Save to database
        result = supabase.table(INTERNSHIPS_TABLE).insert(internship_data).execute()
        
        if not result.data:
            return None
            
        return result.data[0]
        
    except Exception as e:
        print(f"Error saving internship: {str(e)}")
        return None

def fetch_internships_from_internshala() -> List[Dict[str, Any]]:
    """Scrape internships from Internshala"""
    print("Fetching internships from Internshala...")
    internships = []
    
    try:
        url = "https://internshala.com/internships/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all internship listings
        listings = soup.select('.internship_meta')
        
        for listing in listings:
            try:
                # Extract basic info
                title_elem = listing.select_one('.heading_4_5')
                company_elem = listing.select_one('.heading_6')
                location_elem = listing.select_one('.location_link')
                stipend_elem = listing.select_one('.stipend')
                apply_elem = listing.select_one('.view_detail_button')
                posted_elem = listing.select_one('.posted_by_container')
                
                if not all([title_elem, company_elem, location_elem, apply_elem]):
                    continue
                    
                title = title_elem.text.strip()
                company = company_elem.text.strip()
                location = location_elem.text.strip()
                apply_url = f"https://internshala.com{apply_elem['href']}" if apply_elem.has_attr('href') else ""
                
                # Parse stipend
                stipend = {'min': 0, 'max': 0, 'is_unpaid': True}
                if stipend_elem:
                    stipend_text = stipend_elem.text.strip().lower()
                    if 'unpaid' not in stipend_text and 'performance' not in stipend_text:
                        stipend = _parse_stipend(stipend_text)
                
                # Parse posted date
                posted_date = None
                if posted_elem:
                    posted_text = posted_elem.text.strip()
                    posted_date = _parse_posted_date(posted_text)
                
                # Create internship object
                internship = {
                    'title': title,
                    'company': company,
                    'location': location,
                    'type': 'internship',
                    'min_stipend': stipend['min'],
                    'max_stipend': stipend['max'],
                    'is_unpaid': stipend['is_unpaid'],
                    'apply_url': apply_url,
                    'posted_date': posted_date.isoformat() if posted_date else datetime.utcnow().isoformat(),
                    'source': 'Internshala',
                    'is_remote': 'remote' in location.lower(),
                    'is_active': True
                }
                
                internships.append(internship)
                
            except Exception as e:
                print(f"Error processing Internshala listing: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error fetching from Internshala: {str(e)}")
        
    return internships

def fetch_internships_from_themuse() -> List[Dict[str, Any]]:
    """Fetch internships from The Muse API"""
    print("Fetching internships from The Muse...")
    internships = []
    
    try:
        api_key = os.getenv('THE_MUSE_API_KEY')
        if not api_key:
            print("THE_MUSE_API_KEY not found in environment variables")
            return []
            
        url = "https://api-v2.themuse.com/jobs"
        params = {
            'api_key': api_key,
            'category': 'Internship',
            'page': 0,
            'descending': True
        }
        
        # Get first page to know total pages
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        total_pages = data.get('page_count', 1)
        
        # Fetch all pages (limit to 5 pages to avoid rate limiting)
        for page in range(min(5, total_pages)):
            params['page'] = page
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            for job in data.get('results', []):
                try:
                    # Parse location
                    locations = job.get('locations', [])
                    location = locations[0].get('name', 'Remote') if locations else 'Remote'
                    
                    # Parse salary
                    salary = job.get('remuneration', {})
                    min_salary = salary.get('min_amount', 0) if salary else 0
                    max_salary = salary.get('max_amount', 0) if salary else 0
                    
                    # Create internship object
                    internship = {
                        'title': job.get('name', 'Internship Position'),
                        'company': job.get('company', {}).get('name', 'Company'),
                        'location': location,
                        'type': 'internship',
                        'min_stipend': min_salary,
                        'max_stipend': max_salary,
                        'is_unpaid': min_salary == 0 and max_salary == 0,
                        'apply_url': job.get('refs', {}).get('landing_page', ''),
                        'posted_date': job.get('publication_date', datetime.utcnow().isoformat()),
                        'description': job.get('contents', ''),
                        'source': 'The Muse',
                        'is_remote': any('remote' in loc.get('name', '').lower() for loc in locations),
                        'is_active': True
                    }
                    
                    internships.append(internship)
                    
                except Exception as e:
                    print(f"Error processing The Muse job: {str(e)}")
                    continue
                    
    except Exception as e:
        print(f"Error fetching from The Muse: {str(e)}")
        
    return internships

def fetch_internships_from_remotive() -> List[Dict[str, Any]]:
    """Fetch internships from Remotive API"""
    print("Fetching internships from Remotive...")
    internships = []
    
    try:
        url = "https://remotive.com/api/remote-jobs"
        params = {
            'category': 'internship',
            'limit': 50
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        for job in data.get('jobs', []):
            try:
                # Parse salary
                salary = job.get('salary', '')
                min_salary = 0
                max_salary = 0
                is_unpaid = True
                
                if salary and salary.lower() != 'no salary data':
                    try:
                        # Try to parse salary range like "$50k - $70k"
                        numbers = [int(s.replace('$', '').replace('k', '000').replace(',', '')) 
                                 for s in re.findall(r'\$[\d,]+[kK]?', salary)]
                        if numbers:
                            min_salary = min(numbers)
                            max_salary = max(numbers)
                            is_unpaid = False
                    except (ValueError, AttributeError):
                        pass
                
                # Create internship object
                internship = {
                    'title': job.get('title', 'Internship Position'),
                    'company': job.get('company_name', 'Company'),
                    'location': job.get('candidate_required_location', 'Remote'),
                    'type': 'internship',
                    'min_stipend': min_salary,
                    'max_stipend': max_salary,
                    'is_unpaid': is_unpaid,
                    'apply_url': job.get('url', ''),
                    'posted_date': job.get('publication_date', datetime.utcnow().isoformat()),
                    'description': job.get('description', ''),
                    'source': 'Remotive',
                    'is_remote': True,  # All Remotive jobs are remote
                    'is_active': True
                }
                
                internships.append(internship)
                
            except Exception as e:
                print(f"Error processing Remotive job: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error fetching from Remotive: {str(e)}")
        
    return internships

def fetch_all_internships(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Fetch internships from all sources with fallback logic"""
    all_internships = []
    
    # Try to get internships from the database first (unless force_refresh is True)
    if not force_refresh:
        try:
            result = supabase.table(INTERNSHIPS_TABLE) \
                .select('*') \
                .eq('is_active', True) \
                .order('posted_date', desc=True) \
                .limit(100) \
                .execute()
                
            if result.data:
                print(f"Found {len(result.data)} internships in database")
                return result.data
                
        except Exception as e:
            print(f"Error fetching from database: {str(e)}")
    
    # If no internships in database or force_refresh is True, fetch from external sources
    print("Fetching internships from external sources...")
    
    # Fetch from multiple sources in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_internshala = executor.submit(fetch_internships_from_internshala)
        future_themuse = executor.submit(fetch_internships_from_themuse)
        future_remotive = executor.submit(fetch_internships_from_remotive)
        
        try:
            all_internships.extend(future_internshala.result())
        except Exception as e:
            print(f"Error getting Internshala results: {str(e)}")
            
        try:
            all_internships.extend(future_themuse.result())
        except Exception as e:
            print(f"Error getting The Muse results: {str(e)}")
            
        try:
            all_internships.extend(future_remotive.result())
        except Exception as e:
            print(f"Error getting Remotive results: {str(e)}")
    
    # Save to database for future use
    if all_internships:
        try:
            # Clear existing internships
            supabase.table(INTERNSHIPS_TABLE).delete().neq('id', 0).execute()
            
            # Insert new internships (in batches to avoid timeouts)
            batch_size = 20
            for i in range(0, len(all_internships), batch_size):
                batch = all_internships[i:i + batch_size]
                for internship in batch:
                    _save_internship_opportunity(internship)
                print(f"Saved batch {i//batch_size + 1}/{(len(all_internships)-1)//batch_size + 1}")
                
            print(f"Saved {len(all_internships)} internships to database")
            
        except Exception as e:
            print(f"Error saving internships to database: {str(e)}")
    
    return all_internships

@bp.route('', methods=['GET', 'OPTIONS'])
@bp.route('/internships', methods=['GET', 'OPTIONS'])
def get_internships():
    """API endpoint to get all internships with optional filtering"""
    try:
        # Handle preflight request
        if request.method == 'OPTIONS':
            response = make_response()
            return add_cors_headers(response)
            
        # Get query parameters
        is_remote = request.args.get('remote', '').lower() == 'true'
        min_stipend = float(request.args.get('min_stipend', 0))
        max_stipend = float(request.args.get('max_stipend', float('inf')))
        search = request.args.get('search', '').lower()
        
        # Fetch from all sources directly (bypass database)
        print("Fetching internships directly from external sources...")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_internshala = executor.submit(fetch_internships_from_internshala)
            future_themuse = executor.submit(fetch_internships_from_themuse)
            future_remotive = executor.submit(fetch_internships_from_remotive)
            
            all_internships = []
            try:
                all_internships.extend(future_internshala.result())
            except Exception as e:
                print(f"Error getting Internshala results: {str(e)}")
                
            try:
                all_internships.extend(future_themuse.result())
            except Exception as e:
                print(f"Error getting The Muse results: {str(e)}")
                
            try:
                all_internships.extend(future_remotive.result())
            except Exception as e:
                print(f"Error getting Remotive results: {str(e)}")
        
        print(f"Fetched {len(all_internships)} internships from external sources")
        
        # Apply filters
        filtered_internships = []
        for internship in all_internships:
            # Skip if doesn't match remote filter
            if is_remote and not internship.get('is_remote', False):
                continue
                
            # Skip if doesn't match stipend range
            if (internship.get('min_stipend', 0) < min_stipend or 
                internship.get('max_stipend', 0) > max_stipend):
                continue
                
            # Skip if doesn't match search query
            if search and (search not in internship.get('title', '').lower() and 
                          search not in internship.get('company', '').lower() and 
                          search not in internship.get('description', '').lower()):
                continue
                
            filtered_internships.append(internship)
        
        # Add CORS headers to the response
        response = jsonify({
            'success': True,
            'data': filtered_internships,
            'count': len(filtered_internships),
            'total': len(all_internships)
        })
        
        return add_cors_headers(response)
        
    except Exception as e:
        print(f"Error in get_internships: {str(e)}")
        response = jsonify({
            'success': False,
            'error': 'Failed to fetch internships',
            'message': str(e)
        })
        response.status_code = 500
        return add_cors_headers(response)

@bp.route('/sync', methods=['POST'])
def sync_internships():
    """Force sync internships from external sources"""
    try:
        # Force refresh from external sources
        all_internships = fetch_all_internships(force_refresh=True)
        
        return jsonify({
            'success': True,
            'message': f'Successfully synced {len(all_internships)} internships',
            'count': len(all_internships)
        })
        
    except Exception as e:
        print(f"Error syncing internships: {str(e)}")
        response = jsonify({
            'success': False,
            'error': 'Failed to sync internships',
            'message': str(e)
        })
        response.status_code = 500
        return add_cors_headers(response)

@bp.route('/refresh', methods=['GET', 'POST'])
def refresh_internships():
    """Manually trigger a refresh of internships data"""
    try:
        # Force refresh from external sources
        all_internships = fetch_all_internships(force_refresh=True)
        
        return jsonify({
            'success': True,
            'message': f'Successfully refreshed {len(all_internships)} internships',
            'count': len(all_internships),
            'internships': all_internships[:10]  # Return first 10 for preview
        })
        
    except Exception as e:
        print(f"Error refreshing internships: {str(e)}")
        response = jsonify({
            'success': False,
            'error': 'Failed to refresh internships',
            'message': str(e)
        })
        response.status_code = 500
        return add_cors_headers(response)
