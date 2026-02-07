#!/usr/bin/env python3
"""
Complete Verification of Transport Attendance Data Fetching
Tests the entire data flow: Database → Backend → API → Frontend
"""

import requests
import json
from datetime import datetime, date
import sys
import os

def test_api_endpoint():
    """Test the transport attendance API endpoint directly"""
    print("🔍 Testing API Endpoint: /api/transport/attendance")

    try:
        base_url = "http://localhost:5001"
        endpoint = "/api/transport/attendance"

        # Test with today's date
        today = date.today().isoformat()
        params = {'date': today}

        print(f"   Making request to: {base_url}{endpoint} with date={today}")

        response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)

        print(f"   Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   API success: {data.get('success', False)}")

            if data.get('success'):
                attendance_data = data.get('data', [])
                total = data.get('total', 0)

                print(f"   Total records returned: {total}")
                print(f"   Records in response: {len(attendance_data)}")

                if attendance_data:
                    print("   ✅ API returns actual records!")
                    print("   Sample record structure:")
                    sample = attendance_data[0]
                    print(f"     ID: {sample.get('id')}")
                    print(f"     Date: {sample.get('date')}")
                    print(f"     Entity Type: {sample.get('entity_type')}")
                    print(f"     Entity ID: {sample.get('entity_id')}")
                    print(f"     Entity Name: {sample.get('entity_name')}")
                    print(f"     Route ID: {sample.get('route_id')}")
                    print(f"     Bus Number: {sample.get('bus_number')}")
                    print(f"     Status: {sample.get('status')}")
                    print(f"     Remarks: {sample.get('remarks', 'N/A')}")
                    print(f"     Created At: {sample.get('created_at')}")
                    print(f"     Updated At: {sample.get('updated_at')}")

                    return True, attendance_data
                else:
                    print("   ⚠️  API returns empty array - no attendance data for today")
                    return True, []
            else:
                print(f"   ❌ API returned error: {data.get('error', 'Unknown error')}")
                return False, None
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None

    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error: Backend server not running")
        return False, None
    except Exception as e:
        print(f"   ❌ Error testing API: {e}")
        return False, None

def verify_column_names(attendance_data):
    """Verify that column names match the expected schema"""
    print("\n🔍 Verifying Column Names Match Schema")

    expected_columns = {
        'id', 'date', 'entity_type', 'entity_id', 'entity_name',
        'route_id', 'bus_number', 'status', 'remarks', 'created_at', 'updated_at'
    }

    if not attendance_data:
        print("   ⚠️  No data to verify columns")
        return False

    sample_record = attendance_data[0]
    actual_columns = set(sample_record.keys())

    print(f"   Expected columns: {sorted(expected_columns)}")
    print(f"   Actual columns: {sorted(actual_columns)}")

    missing_columns = expected_columns - actual_columns
    extra_columns = actual_columns - expected_columns

    if missing_columns:
        print(f"   ❌ Missing columns: {missing_columns}")
        return False

    if extra_columns:
        print(f"   ⚠️  Extra columns: {extra_columns}")

    print("   ✅ Column names match expected schema!")
    return True

def test_frontend_service():
    """Test the frontend service method"""
    print("\n🔍 Testing Frontend Service Integration")

    # Since we can't run the actual React frontend, we'll simulate the service call
    # by making the same HTTP request that the frontend would make

    try:
        # This simulates what TransportService.getAttendance() does
        base_url = "http://localhost:5001"
        endpoint = "/api/transport/attendance"
        today = date.today().isoformat()

        print(f"   Simulating frontend service call to: {base_url}{endpoint}?date={today}")

        response = requests.get(f"{base_url}{endpoint}", params={'date': today}, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                attendance_data = data.get('data', [])
                print(f"   ✅ Frontend service would receive {len(attendance_data)} records")
                return True, attendance_data
            else:
                print(f"   ❌ Frontend service would receive error: {data.get('error')}")
                return False, None
        else:
            print(f"   ❌ Frontend service would fail with HTTP {response.status_code}")
            return False, None

    except Exception as e:
        print(f"   ❌ Frontend service simulation failed: {e}")
        return False, None

def check_database_directly():
    """Check the database directly to confirm data exists"""
    print("\n🔍 Checking Database Directly")

    try:
        # Import the Supabase client
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
        from backend.supabase_client import get_supabase

        supabase = get_supabase()

        # Query the transport_attendance table
        response = supabase.table('transport_attendance').select('*', count='exact').execute()

        total_count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0

        print(f"   Total records in transport_attendance table: {total_count}")

        if response.data and len(response.data) > 0:
            print("   ✅ Database contains attendance data!")
            print("   Sample record from database:")
            sample = response.data[0]
            print(f"     ID: {sample.get('id')}")
            print(f"     Date: {sample.get('date')}")
            print(f"     Entity Type: {sample.get('entity_type')}")
            print(f"     Status: {sample.get('status')}")

            return True, response.data
        else:
            print("   ❌ Database is empty - no attendance records found")
            return False, None

    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        return False, None

def main():
    """Main verification function"""
    print("🚀 Complete Transport Attendance Data Fetching Verification")
    print("=" * 60)

    results = {
        'database_check': False,
        'api_endpoint': False,
        'column_verification': False,
        'frontend_service': False
    }

    # 1. Check database directly
    db_success, db_data = check_database_directly()
    results['database_check'] = db_success

    # 2. Test API endpoint
    api_success, api_data = test_api_endpoint()
    results['api_endpoint'] = api_success

    # 3. Verify column names
    if api_success and api_data:
        column_success = verify_column_names(api_data)
        results['column_verification'] = column_success
    else:
        print("\n🔍 Skipping column verification - no API data")
        results['column_verification'] = False

    # 4. Test frontend service
    frontend_success, frontend_data = test_frontend_service()
    results['frontend_service'] = frontend_success

    # Final summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS")
    print("=" * 60)

    all_passed = all(results.values())

    print(f"Database Check: {'✅ PASS' if results['database_check'] else '❌ FAIL'}")
    print(f"API Endpoint: {'✅ PASS' if results['api_endpoint'] else '❌ FAIL'}")
    print(f"Column Verification: {'✅ PASS' if results['column_verification'] else '❌ FAIL'}")
    print(f"Frontend Service: {'✅ PASS' if results['frontend_service'] else '❌ FAIL'}")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SUCCESS: Data from transport_attendance is successfully fetched and available!")
        print("✅ Database → Backend → API → Frontend data flow is working correctly")
    else:
        print("❌ FAILURE: Issues found in the data fetching pipeline")

        if not results['database_check']:
            print("   - Database: No data in transport_attendance table")
        if not results['api_endpoint']:
            print("   - Backend API: Endpoint not responding or returning errors")
        if not results['column_verification']:
            print("   - Schema: Column names don't match expected schema")
        if not results['frontend_service']:
            print("   - Frontend: Service cannot fetch data from API")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
