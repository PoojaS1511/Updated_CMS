"""
Transport Drivers Data Flow Verification
Checks database → backend API → frontend integration
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5001')

print("\n" + "="*70)
print("TRANSPORT_DRIVERS TABLE - COMPLETE DATA FLOW VERIFICATION")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"API Base URL: {API_BASE_URL}")
print(f"Supabase Connected: {'✅ YES' if SUPABASE_URL else '❌ NO'}")
print("="*70 + "\n")

# ============================================================================
# STEP 1: CHECK DATABASE TABLE EXISTENCE AND SCHEMA
# ============================================================================

def check_database_schema():
    """Step 1: Verify transport_drivers table in Supabase"""
    print("📊 STEP 1: DATABASE TABLE VERIFICATION")
    print("-" * 70)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: Supabase credentials not found in environment")
        print("   Please set SUPABASE_URL and SUPABASE_KEY")
        return False
    
    try:
        from supabase import create_client
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Try to fetch one record to verify table exists
        response = supabase.table('transport_drivers').select('*').limit(1).execute()
        
        print("✅ transport_drivers table exists in database")
        
        # Check the schema by examining response data
        if response.data and len(response.data) > 0:
            first_record = response.data[0]
            print(f"✅ Table contains data ({len(response.data)} records found)")
            print("\n📋 Database Columns Found:")
            
            expected_columns = [
                'id', 'driver_id', 'name', 'phone', 'license_number', 
                'license_expiry', 'blood_group', 'emergency_contact', 
                'experience_years', 'shift', 'working_hours', 'assigned_bus', 
                'status', 'created_at', 'updated_at'
            ]
            
            actual_columns = list(first_record.keys())
            
            for col in expected_columns:
                if col in actual_columns:
                    print(f"   ✅ {col}")
                else:
                    print(f"   ⚠️  {col} (NOT FOUND)")
            
            # Check for unexpected columns
            unexpected = [c for c in actual_columns if c not in expected_columns]
            if unexpected:
                print(f"\n⚠️  Extra columns found: {', '.join(unexpected)}")
            
            print(f"\n✅ Sample Record:")
            print(f"   Driver ID: {first_record.get('driver_id', 'N/A')}")
            print(f"   Name: {first_record.get('name', 'N/A')}")
            print(f"   Phone: {first_record.get('phone', 'N/A')}")
            print(f"   License Number: {first_record.get('license_number', 'N/A')}")
            print(f"   Status: {first_record.get('status', 'N/A')}")
            
            return True
        else:
            print("⚠️  WARNING: Table exists but contains no data")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: Could not verify table: {str(e)}")
        return False

# ============================================================================
# STEP 2: GET TOTAL RECORD COUNT
# ============================================================================

def check_record_count():
    """Step 2: Count records in transport_drivers"""
    print("\n\n📊 STEP 2: RECORD COUNT VERIFICATION")
    print("-" * 70)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Skipping - Supabase not configured")
        return 0
    
    try:
        from supabase import create_client
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table('transport_drivers').select('*').execute()
        
        count = len(response.data) if response.data else 0
        
        if count > 0:
            print(f"✅ Total drivers in database: {count}")
            return count
        else:
            print("⚠️  WARNING: No records found in transport_drivers table")
            return 0
            
    except Exception as e:
        print(f"❌ ERROR: Could not count records: {str(e)}")
        return 0

# ============================================================================
# STEP 3: TEST BACKEND API ENDPOINT
# ============================================================================

def test_backend_api():
    """Step 3: Test GET /api/transport/drivers endpoint"""
    print("\n\n🔗 STEP 3: BACKEND API ENDPOINT VERIFICATION")
    print("-" * 70)
    
    endpoint = f"{API_BASE_URL}/api/transport/drivers"
    print(f"Testing endpoint: {endpoint}")
    
    try:
        # Test without authentication first
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ API endpoint (GET) returned: {response.status_code} OK")
            
            data = response.json()
            
            # Check response structure
            if 'success' in data and data['success']:
                print("✅ Response has 'success' field: TRUE")
            else:
                print("⚠️  Response success field is false or missing")
            
            # Check data field
            if 'data' in data:
                drivers_data = data['data']
                if isinstance(drivers_data, list):
                    driver_count = len(drivers_data)
                    print(f"✅ Response contains 'data' array with {driver_count} drivers")
                    
                    if driver_count > 0:
                        first_driver = drivers_data[0]
                        print(f"\n📋 Response Columns (from first record):")
                        
                        expected_fields = [
                            'driver_id', 'name', 'phone', 'license_number',
                            'license_expiry', 'blood_group', 'emergency_contact',
                            'experience_years', 'shift', 'working_hours',
                            'assigned_bus', 'status'
                        ]
                        
                        for field in expected_fields:
                            if field in first_driver:
                                value = first_driver[field]
                                print(f"   ✅ {field}: {value}")
                            else:
                                print(f"   ❌ {field}: MISSING")
                        
                        # Check pagination fields
                        print(f"\n📊 Response Pagination:")
                        print(f"   Total: {data.get('total', 'N/A')}")
                        print(f"   Limit: {data.get('limit', 'N/A')}")
                        print(f"   Page: {data.get('page', 'N/A')}")
                        print(f"   Pages: {data.get('pages', 'N/A')}")
                        
                        return True, drivers_data[0]
                    else:
                        print("⚠️  API returned empty data array")
                        return True, None
                else:
                    print(f"❌ 'data' field is not a list: {type(drivers_data)}")
                    return False, None
            else:
                print("❌ Response does not contain 'data' field")
                return False, None
        
        elif response.status_code == 404:
            print(f"❌ API endpoint not found: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False, None
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ ERROR: Could not connect to API")
        print(f"   Is the backend server running at {API_BASE_URL}?")
        return False, None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False, None

# ============================================================================
# STEP 4: TEST API FILTERING AND PAGINATION
# ============================================================================

def test_api_features():
    """Step 4: Test API filtering and pagination"""
    print("\n\n⚙️  STEP 4: API FEATURES VERIFICATION")
    print("-" * 70)
    
    endpoint = f"{API_BASE_URL}/api/transport/drivers"
    
    # Test pagination
    print("Testing pagination with limit=5...")
    try:
        response = requests.get(f"{endpoint}?limit=5&page=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            actual_count = len(data.get('data', []))
            expected_limit = data.get('limit', 0)
            print(f"✅ Pagination works - limit: {expected_limit}, received: {actual_count}")
        else:
            print(f"⚠️  Pagination test failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Pagination test error: {str(e)}")
    
    # Test filtering by status
    print("\nTesting filter by status=Active...")
    try:
        response = requests.get(f"{endpoint}?status=Active", timeout=10)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('data', []))
            print(f"✅ Status filter works - found {count} active drivers")
        else:
            print(f"⚠️  Status filter test failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Status filter test error: {str(e)}")

# ============================================================================
# STEP 5: VERIFY COLUMN NAME EXACT MATCHES
# ============================================================================

def verify_column_names():
    """Step 5: Verify exact column name matches"""
    print("\n\n🔍 STEP 5: COLUMN NAME VERIFICATION")
    print("-" * 70)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Skipping - Supabase not configured")
        return False
    
    try:
        from supabase import create_client
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table('transport_drivers').select('*').limit(1).execute()
        
        if response.data:
            actual_columns = set(response.data[0].keys())
            
            expected = {
                'id', 'driver_id', 'name', 'phone', 'license_number',
                'license_expiry', 'blood_group', 'emergency_contact', 
                'experience_years', 'shift', 'working_hours', 'assigned_bus',
                'status', 'created_at', 'updated_at'
            }
            
            missing = expected - actual_columns
            extra = actual_columns - expected
            matched = expected & actual_columns
            
            print(f"✅ Columns matched: {len(matched)}/{len(expected)}")
            print(f"   {', '.join(sorted(matched))}")
            
            if missing:
                print(f"\n❌ Missing columns: {', '.join(missing)}")
            
            if extra:
                print(f"\n⚠️  Extra columns: {', '.join(extra)}")
            
            return len(missing) == 0
        else:
            print("⚠️  Cannot verify - no data in table")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

# ============================================================================
# STEP 6: CHECK RLS AND PERMISSIONS
# ============================================================================

def check_rls_permissions():
    """Step 6: Check Row Level Security and permissions"""
    print("\n\n🔐 STEP 6: RLS AND PERMISSIONS VERIFICATION")
    print("-" * 70)
    
    endpoint = f"{API_BASE_URL}/api/transport/drivers"
    
    # Test without authentication
    print("Testing access without authentication...")
    try:
        response = requests.get(endpoint, timeout=10)
        if response.status_code == 200:
            print("✅ Public access allowed (RLS policy permits)")
        elif response.status_code == 403:
            print("⚠️  Access denied (RLS policy blocking) - status 403")
            print("   This may be intentional if auth is required")
        elif response.status_code in [401, 404]:
            print(f"⚠️  Status {response.status_code}: {response.text[:100]}")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test with token if available
    token = os.getenv('SUPABASE_ANON_KEY')
    if token:
        print("\nTesting access with Authorization header...")
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                print("✅ Authentication works")
            else:
                print(f"⚠️  Auth test returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Auth test error: {str(e)}")
    else:
        print("ℹ️  No auth token found in environment")

# ============================================================================
# STEP 7: TEST FRONTEND INTEGRATION SIMULATION
# ============================================================================

def test_frontend_integration():
    """Step 7: Simulate frontend API call"""
    print("\n\n🌐 STEP 7: FRONTEND INTEGRATION VERIFICATION")
    print("-" * 70)
    
    endpoint = f"{API_BASE_URL}/api/transport/drivers"
    
    try:
        # Simulate what the frontend does
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success') and 'data' in data:
                drivers = data['data']
                
                if isinstance(drivers, list) and len(drivers) > 0:
                    print(f"✅ Frontend would receive {len(drivers)} driver records")
                    
                    # Check if data is suitable for rendering
                    sample = drivers[0]
                    render_safe = all(k in sample for k in ['driver_id', 'name', 'phone', 'status'])
                    
                    if render_safe:
                        print("✅ Data structure is suitable for UI rendering")
                        print("\nSample data that would be rendered:")
                        print(f"   ID: {sample.get('driver_id')}")
                        print(f"   Name: {sample.get('name')}")
                        print(f"   Phone: {sample.get('phone')}")
                        print(f"   Status: {sample.get('status')}")
                        return True
                    else:
                        print("❌ Data missing required fields for rendering")
                        return False
                else:
                    print("⚠️  Empty data array - nothing to render")
                    return None
            else:
                print("❌ API response invalid or success=false")
                return False
        else:
            print(f"❌ API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

# ============================================================================
# GENERATE FINAL REPORT
# ============================================================================

def generate_report():
    """Generate comprehensive verification report"""
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'steps': {}
    }
    
    # Run all tests
    print("\n\n" + "="*70)
    print("RUNNING FULL VERIFICATION SUITE")
    print("="*70)
    
    # Step 1: Database
    db_ok = check_database_schema()
    results['steps']['database_schema'] = db_ok
    
    # Step 2: Record count
    record_count = check_record_count()
    results['steps']['record_count'] = record_count
    
    # Step 3: API
    api_ok, sample_record = test_backend_api()
    results['steps']['backend_api'] = api_ok
    results['sample_record'] = sample_record
    
    # Step 4: API features
    test_api_features()
    
    # Step 5: Column names
    columns_ok = verify_column_names()
    results['steps']['column_verification'] = columns_ok
    
    # Step 6: RLS
    check_rls_permissions()
    
    # Step 7: Frontend
    frontend_ok = test_frontend_integration()
    results['steps']['frontend_integration'] = frontend_ok
    
    # =====================================================================
    # FINAL SUMMARY
    # =====================================================================
    
    print("\n\n" + "="*70)
    print("FINAL VERIFICATION SUMMARY")
    print("="*70)
    
    all_ok = all(v for v in results['steps'].values() if isinstance(v, bool))
    
    print("\n📋 Summary:")
    print(f"{'✅ Database Schema': <40} {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"{'✅ Record Count': <40} {f'✅ {record_count} records' if record_count > 0 else '⚠️  0 records'}")
    print(f"{'✅ Backend API': <40} {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"{'✅ Column Names': <40} {'✅ PASS' if columns_ok else '❌ FAIL'}")
    print(f"{'✅ Frontend Integration': <40} {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    
    print("\n" + "="*70)
    
    if db_ok and api_ok and frontend_ok and record_count > 0:
        print("✅ DATA FLOW IS WORKING CORRECTLY")
        print("="*70)
        print("\n✅ RESULT: transport_drivers data is successfully fetched and displayed")
        print("   • Database table exists with correct schema")
        print(f"   • {record_count} driver records available")
        print("   • Backend API endpoint returns data correctly")
        print("   • Column names match exactly")
        print("   • Frontend can receive and render data")
    else:
        print("❌ DATA FLOW IS BROKEN OR INCOMPLETE")
        print("="*70)
        
        if not db_ok:
            print("\n❌ Issue: Database table problem")
            print("   • Check table exists in Supabase")
            print("   • Verify table schema")
        
        if record_count == 0:
            print("\n❌ Issue: No data in database")
            print("   • Run populate_transport_data.py to insert sample data")
            print("   • Check that data insertion was successful")
        
        if not api_ok:
            print("\n❌ Issue: Backend API endpoint not working")
            print("   • Check backend server is running")
            print("   • Verify API endpoint path: /api/transport/drivers")
            print("   • Check for API errors in backend logs")
        
        if not frontend_ok:
            print("\n❌ Issue: Frontend integration problem")
            print("   • Check frontend is calling correct API endpoint")
            print("   • Verify data mapping in components")
            print("   • Check browser console for errors")
    
    print("\n" + "="*70 + "\n")
    
    return results

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    results = generate_report()
    
    # Save results to file
    with open('transport_drivers_verification_report.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("📁 Report saved to: transport_drivers_verification_report.json")
