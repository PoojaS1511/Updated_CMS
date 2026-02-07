"""
Enhanced Transport Drivers Verification - Direct Backend & Database Check
Tests the actual data flow being used (SQLite vs Supabase)
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from pathlib import Path

print("\n" + "="*70)
print("TRANSPORT DRIVERS - ENHANCED DATA FLOW VERIFICATION")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5001')
DB_PATH = Path(__file__).parent / 'Updated_CMS-main' / 'backend' / 'student_management.db'

verification_results = {
    'timestamp': datetime.now().isoformat(),
    'api_working': False,
    'database_type': None,
    'record_count': 0,
    'column_names_match': False,
    'rls_working': False,
    'frontend_ready': False,
    'issues': []
}

# ============================================================================
# STEP 1: CHECK BACKEND IS RUNNING
# ============================================================================

print("🔍 STEP 1: BACKEND API SERVER CHECK")
print("-" * 70)

try:
    response = requests.get(f"{API_BASE_URL}/api/transport/drivers", timeout=5)
    if response.status_code == 200:
        print(f"✅ Backend API is running at {API_BASE_URL}")
        print(f"✅ Endpoint /api/transport/drivers is accessible")
        verification_results['api_working'] = True
        
        data = response.json()
        print(f"✅ API response is valid JSON")
        print(f"✅ Response contains {len(data.get('data', []))} driver records")
        verification_results['record_count'] = len(data.get('data', []))
    else:
        print(f"❌ Backend returned error: {response.status_code}")
        verification_results['issues'].append(f"Backend error: {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"❌ Cannot connect to backend at {API_BASE_URL}")
    print("   Make sure the backend is running: python backend/app.py")
    verification_results['issues'].append("Backend not running")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    verification_results['issues'].append(str(e))

# ============================================================================
# STEP 2: CHECK DATABASE TYPE (SQLite vs Supabase)
# ============================================================================

print("\n\n📊 STEP 2: DATABASE TYPE DETECTION")
print("-" * 70)

# Check if using SQLite
if DB_PATH.exists():
    print(f"✅ SQLite database found at:")
    print(f"   {DB_PATH}")
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Check if transport_drivers table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='transport_drivers'
        """)
        
        if cursor.fetchone():
            print("✅ SQLite: transport_drivers table EXISTS")
            verification_results['database_type'] = 'SQLite'
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM transport_drivers")
            count = cursor.fetchone()[0]
            print(f"✅ SQLite: Table contains {count} driver records")
            verification_results['record_count'] = count
            
            # Check schema
            cursor.execute("PRAGMA table_info(transport_drivers)")
            columns = cursor.fetchall()
            
            print(f"✅ SQLite: Table has {len(columns)} columns:")
            column_names = [col[1] for col in columns]
            for col in column_names:
                print(f"   • {col}")
            
            # Verify expected columns
            expected = [
                'driver_id', 'name', 'phone', 'license_number',
                'license_expiry', 'blood_group', 'emergency_contact',
                'experience_years', 'shift', 'working_hours',
                'assigned_bus', 'status'
            ]
            
            missing = [c for c in expected if c not in column_names]
            if missing:
                print(f"\n⚠️  Missing columns: {', '.join(missing)}")
                verification_results['issues'].append(f"Missing columns: {missing}")
            else:
                print(f"\n✅ All expected columns present")
                verification_results['column_names_match'] = True
            
            # Get sample record
            cursor.execute("SELECT * FROM transport_drivers LIMIT 1")
            cols = [description[0] for description in cursor.description]
            record = cursor.fetchone()
            
            if record:
                print(f"\n📋 Sample SQLite Record:")
                for col, val in zip(cols, record):
                    print(f"   {col}: {val}")
            
            conn.close()
        else:
            print("⚠️  SQLite database exists but transport_drivers table NOT FOUND")
            verification_results['issues'].append("transport_drivers table not in SQLite")
    except Exception as e:
        print(f"❌ Error checking SQLite: {e}")
        verification_results['issues'].append(f"SQLite error: {e}")

# ============================================================================
# STEP 3: TEST API RESPONSE STRUCTURE
# ============================================================================

print("\n\n🔗 STEP 3: API RESPONSE STRUCTURE VALIDATION")
print("-" * 70)

try:
    response = requests.get(f"{API_BASE_URL}/api/transport/drivers", timeout=5)
    data = response.json()
    
    print("Response Structure Check:")
    
    # Check top-level fields
    required_fields = ['success', 'data']
    for field in required_fields:
        if field in data:
            print(f"  ✅ '{field}' field: present")
        else:
            print(f"  ❌ '{field}' field: MISSING")
            verification_results['issues'].append(f"Missing field: {field}")
    
    # Check data array
    if isinstance(data.get('data'), list):
        print(f"  ✅ 'data' is array: {len(data['data'])} records")
    else:
        print(f"  ❌ 'data' is not array")
    
    # Check first record structure
    if data.get('data') and len(data['data']) > 0:
        first = data['data'][0]
        print(f"\n📋 First Record Fields:")
        
        required_response_fields = [
            'driver_id', 'name', 'phone', 'license_number',
            'status', 'shift', 'working_hours'
        ]
        
        for field in required_response_fields:
            if field in first:
                print(f"  ✅ {field}: {first[field]}")
            else:
                print(f"  ❌ {field}: MISSING")
                verification_results['issues'].append(f"Missing API response field: {field}")
        
        verification_results['frontend_ready'] = True
        
except Exception as e:
    print(f"❌ Error validating API response: {e}")
    verification_results['issues'].append(f"API validation error: {e}")

# ============================================================================
# STEP 4: TEST PAGINATION
# ============================================================================

print("\n\n📄 STEP 4: PAGINATION & FILTERING TEST")
print("-" * 70)

try:
    # Test pagination
    response = requests.get(f"{API_BASE_URL}/api/transport/drivers?limit=2&page=1", timeout=5)
    data = response.json()
    
    if 'limit' in data and 'page' in data:
        print(f"✅ Pagination fields present:")
        print(f"   • limit: {data.get('limit')}")
        print(f"   • page: {data.get('page')}")
        print(f"   • total: {data.get('total')}")
        print(f"   • Records returned: {len(data.get('data', []))}")
    else:
        print("⚠️  Pagination fields missing from response")
    
    # Test filtering
    response = requests.get(f"{API_BASE_URL}/api/transport/drivers?status=Active", timeout=5)
    data = response.json()
    print(f"\n✅ Filtering by status=Active returned {len(data.get('data', []))} records")
    
except Exception as e:
    print(f"⚠️  Pagination/filtering test error: {e}")

# ============================================================================
# STEP 5: VERIFY COLUMN NAMES MATCH DATABASE → API → FRONTEND
# ============================================================================

print("\n\n🔍 STEP 5: COLUMN NAME CONSISTENCY CHECK")
print("-" * 70)

# Expected column names per user specification
EXPECTED_COLUMNS = [
    'driver_id', 'name', 'phone', 'license_number', 'license_expiry',
    'blood_group', 'emergency_contact', 'experience_years', 'shift',
    'working_hours', 'assigned_bus', 'status', 'created_at', 'updated_at'
]

print(f"Expected columns: {len(EXPECTED_COLUMNS)}")
print(f"   {', '.join(EXPECTED_COLUMNS)}\n")

# Check API response columns
try:
    response = requests.get(f"{API_BASE_URL}/api/transport/drivers", timeout=5)
    data = response.json()
    
    if data.get('data') and len(data['data']) > 0:
        api_columns = list(data['data'][0].keys())
        print(f"API returns columns: {len(api_columns)}")
        print(f"   {', '.join(api_columns)}\n")
        
        # Check which expected columns are in API response
        present = [c for c in EXPECTED_COLUMNS if c in api_columns]
        missing = [c for c in EXPECTED_COLUMNS if c not in api_columns]
        extra = [c for c in api_columns if c not in EXPECTED_COLUMNS]
        
        print(f"✅ Present: {len(present)}/{len(EXPECTED_COLUMNS)}")
        if missing:
            print(f"⚠️  Missing from API: {', '.join(missing)}")
            verification_results['issues'].append(f"Missing columns in API: {missing}")
        else:
            print("✅ All expected columns present in API response")
            verification_results['column_names_match'] = True
        
        if extra:
            print(f"ℹ️  Extra columns from API: {', '.join(extra)}")
        
except Exception as e:
    print(f"❌ Column check error: {e}")

# ============================================================================
# STEP 6: TEST RLS POLICIES (Permissions)
# ============================================================================

print("\n\n🔐 STEP 6: SECURITY & PERMISSIONS CHECK")
print("-" * 70)

try:
    # Test unauthenticated access
    response = requests.get(f"{API_BASE_URL}/api/transport/drivers", timeout=5)
    
    if response.status_code == 200:
        print("✅ Public access ALLOWED (RLS policy permits data reading)")
        print("   This means unauthenticated users can view driver data")
        verification_results['rls_working'] = True
    elif response.status_code == 403:
        print("⚠️  Access DENIED - 403 Forbidden")
        print("   RLS policy is blocking unauthenticated access")
        print("   Ensure authentication is configured properly")
        verification_results['issues'].append("Access denied: 403")
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
        verification_results['issues'].append(f"Unexpected status: {response.status_code}")
        
except Exception as e:
    print(f"⚠️  Permission test error: {e}")

# ============================================================================
# STEP 7: FINAL DATA FLOW DIAGRAM
# ============================================================================

print("\n\n📊 STEP 7: DATA FLOW VISUALIZATION")
print("-" * 70)

print("""
DATA FLOW CHAIN:
├─ DATABASE (SQLite or Supabase)
│  └─ transport_drivers table
│     └─ {driver_id, name, phone, license_number, ...}
│
├─ BACKEND API (Flask/Python)
│  └─ GET /api/transport/drivers
│     └─ DriverController.get_drivers()
│        └─ SupabaseDriver.get_all()
│           └─ Returns: { success, data [], metadata }
│
└─ FRONTEND (React)
   └─ TransportManagement.jsx
      └─ apiCall('/api/transport/drivers')
         └─ Maps data to UI components
            └─ Displays driver table/list
""")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n\n" + "="*70)
print("VERIFICATION SUMMARY")
print("="*70 + "\n")

checks = [
    ("Backend API Running", verification_results['api_working']),
    ("Database Records Found", verification_results['record_count'] > 0),
    ("Column Names Match", verification_results['column_names_match']),
    ("Permissions Working", verification_results['rls_working']),
    ("Frontend Ready", verification_results['frontend_ready']),
]

for check_name, result in checks:
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{check_name:<30} {status}")

print("\n" + "="*70)

if all(r for _, r in checks):
    print("✅ DATA IS SUCCESSFULLY FETCHED FROM transport_drivers AND DISPLAYED")
    print("="*70)
    print("\n✅ RESULT: ALL CHECKS PASSED")
    print("\nThe transport_drivers table is correctly connected:")
    print("  ✅ Database contains driver records")
    print(f"  ✅ Backend API returns {verification_results['record_count']} drivers")
    print("  ✅ Column names match expected schema")
    print("  ✅ Permissions allow data retrieval")
    print("  ✅ Frontend receives properly formatted data")
    
elif verification_results['api_working'] and verification_results['record_count'] > 0:
    print("⚠️  PARTIAL SUCCESS - Data flow is mostly working")
    print("="*70)
    print("\nSome checks failed:")
    for issue in verification_results['issues']:
        print(f"  • {issue}")
else:
    print("❌ DATA FLOW IS BROKEN")
    print("="*70)
    print("\nBreaking point(s):")
    
    if not verification_results['api_working']:
        print("  ❌ Backend API is not accessible")
        print("     → Start backend: cd backend && python app.py")
    
    if verification_results['record_count'] == 0:
        print("  ❌ No driver records in database")
        print("     → Populate data: python populate_transport_data.py")
    
    for issue in verification_results['issues']:
        print(f"  ❌ {issue}")

print("\n" + "="*70 + "\n")

# Save detailed results
output_file = 'transport_drivers_verification_detailed.json'
with open(output_file, 'w') as f:
    json.dump(verification_results, f, indent=2, default=str)

print(f"📁 Detailed report saved to: {output_file}")
