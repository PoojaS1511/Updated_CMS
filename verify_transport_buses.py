#!/usr/bin/env python3
"""
Verification script for transport_buses table connectivity
Tests the complete data flow: Database → Backend → API → Frontend
"""

import requests
import json
import sys
from datetime import datetime

class TransportBusesVerifier:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.results = {
            'database_check': False,
            'backend_query': False,
            'api_response': False,
            'frontend_receipt': False,
            'column_mapping': False,
            'permissions_check': False
        }
        self.errors = []

    def log(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def check_database_table(self):
        """Check if transport_buses table exists and has data"""
        self.log("Checking database table existence and data...")

        try:
            # Try to query the table directly via API
            response = requests.get(f"{self.api_base}/transport/buses?limit=1", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and isinstance(data.get('data'), list):
                    if len(data['data']) > 0:
                        self.log(f"✅ Database table exists with {data.get('total', 'unknown')} records")
                        self.results['database_check'] = True
                        return True
                    else:
                        self.log("⚠️  Table exists but appears empty")
                        self.results['database_check'] = True  # Table exists, just no data
                        return True
                else:
                    self.errors.append(f"Unexpected API response format: {data}")
            else:
                self.errors.append(f"API returned status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            self.errors.append(f"Network error checking database: {str(e)}")
        except Exception as e:
            self.errors.append(f"Error checking database: {str(e)}")

        return False

    def check_backend_query(self):
        """Check if backend can query transport_buses table"""
        self.log("Checking backend query capability...")

        try:
            # Test the buses endpoint
            response = requests.get(f"{self.api_base}/transport/buses", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log("✅ Backend can successfully query transport_buses table")
                    self.results['backend_query'] = True

                    # Check if we got actual records
                    records = data.get('data', [])
                    if isinstance(records, list) and len(records) > 0:
                        self.log(f"✅ Backend returned {len(records)} bus records")
                        return True
                    else:
                        self.log("⚠️  Backend query successful but returned empty array")
                        return True
                else:
                    self.errors.append(f"Backend returned success=false: {data}")
            else:
                self.errors.append(f"Backend API error: {response.status_code} - {response.text}")

        except Exception as e:
            self.errors.append(f"Error testing backend query: {str(e)}")

        return False

    def check_api_response_format(self):
        """Check if API response contains expected data structure"""
        self.log("Checking API response format and data structure...")

        try:
            response = requests.get(f"{self.api_base}/transport/buses?limit=5", timeout=10)

            if response.status_code == 200:
                data = response.json()

                if not data.get('success'):
                    self.errors.append("API response success is false")
                    return False

                records = data.get('data', [])
                if not isinstance(records, list):
                    self.errors.append("API data is not a list")
                    return False

                if len(records) == 0:
                    self.log("⚠️  API returned empty data array")
                    self.results['api_response'] = True  # API works, just no data
                    return True

                # Check first record structure
                sample_record = records[0]
                expected_columns = [
                    'id', 'bus_number', 'route_id', 'route_name', 'capacity',
                    'driver_id', 'driver_name', 'status', 'last_service',
                    'next_service', 'created_at', 'updated_at'
                ]

                missing_columns = []
                for col in expected_columns:
                    if col not in sample_record:
                        missing_columns.append(col)

                if missing_columns:
                    self.errors.append(f"Missing columns in API response: {missing_columns}")
                    self.log(f"⚠️  Missing columns: {missing_columns}")
                else:
                    self.log("✅ API response contains all expected columns")
                    self.results['column_mapping'] = True

                self.log("✅ API response format is correct")
                self.results['api_response'] = True
                return True

        except Exception as e:
            self.errors.append(f"Error checking API response: {str(e)}")

        return False

    def check_permissions_and_rls(self):
        """Check for permission/RLS issues"""
        self.log("Checking permissions and RLS policies...")

        try:
            # Try different types of queries to check permissions
            endpoints_to_test = [
                f"{self.api_base}/transport/buses",
                f"{self.api_base}/transport/buses?status=Active",
                f"{self.api_base}/transport/buses?limit=1"
            ]

            for endpoint in endpoints_to_test:
                response = requests.get(endpoint, timeout=10)

                if response.status_code in [200, 404]:  # 404 is OK if no data matches filter
                    continue
                elif response.status_code == 401:
                    self.errors.append("Authentication required - check API keys")
                    return False
                elif response.status_code == 403:
                    self.errors.append("Access forbidden - check RLS policies")
                    return False
                elif response.status_code >= 500:
                    self.errors.append(f"Server error: {response.status_code} - {response.text}")
                    return False

            self.log("✅ No permission or RLS issues detected")
            self.results['permissions_check'] = True
            return True

        except Exception as e:
            self.errors.append(f"Error checking permissions: {str(e)}")

        return False

    def check_frontend_receipt(self):
        """Check if frontend can receive and process the API data"""
        self.log("Checking frontend data receipt and processing...")

        try:
            # Since we can't directly test the React frontend, we'll simulate
            # what the frontend does by making the same API call
            response = requests.get(f"{self.api_base}/transport/buses?limit=10", timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('success') and isinstance(data.get('data'), list):
                    records = data['data']

                    # Simulate frontend processing
                    processed_records = []
                    for record in records:
                        # Check if record has required fields for frontend display
                        required_fields = ['id', 'bus_number', 'capacity', 'status']
                        missing_fields = [f for f in required_fields if f not in record]

                        if missing_fields:
                            self.errors.append(f"Record missing required frontend fields: {missing_fields}")
                            continue

                        processed_records.append(record)

                    if processed_records:
                        self.log(f"✅ Frontend can successfully process {len(processed_records)} bus records")
                        self.results['frontend_receipt'] = True
                        return True
                    else:
                        self.log("⚠️  No records could be processed by frontend")
                        self.results['frontend_receipt'] = True  # API works, just no data
                        return True
                else:
                    self.errors.append("Frontend cannot parse API response")
            else:
                self.errors.append(f"Frontend cannot reach API: {response.status_code}")

        except Exception as e:
            self.errors.append(f"Error simulating frontend receipt: {str(e)}")

        return False

    def run_verification(self):
        """Run all verification checks"""
        self.log("🚀 Starting transport_buses table verification...")

        checks = [
            ("Database Table", self.check_database_table),
            ("Backend Query", self.check_backend_query),
            ("API Response", self.check_api_response_format),
            ("Permissions/RLS", self.check_permissions_and_rls),
            ("Frontend Receipt", self.check_frontend_receipt)
        ]

        all_passed = True
        for check_name, check_func in checks:
            self.log(f"\n--- {check_name} Check ---")
            if not check_func():
                all_passed = False

        return self.generate_report(all_passed)

    def generate_report(self, all_passed):
        """Generate final verification report"""
        self.log("\n" + "="*60)
        self.log("VERIFICATION REPORT: transport_buses Table Connectivity")
        self.log("="*60)

        # Overall status
        if all_passed and not self.errors:
            self.log("✅ SUCCESS: Data from transport_buses is successfully fetched and displayed")
            status = "✅ SUCCESS"
        else:
            status = "❌ FAILURE"
            self.log(f"{status}: Data flow has issues")

        # Detailed results
        self.log("\nDetailed Results:")
        for check, passed in self.results.items():
            status_icon = "✅" if passed else "❌"
            self.log(f"  {status_icon} {check.replace('_', ' ').title()}")

        # Errors
        if self.errors:
            self.log("\nIssues Found:")
            for error in self.errors:
                self.log(f"  ❌ {error}")

        # Identify failure layer
        if not all_passed:
            self.log("\nFailure Analysis:")
            if not self.results['database_check']:
                self.log("  🔴 FAILURE LAYER: Database - Table may not exist or be accessible")
            elif not self.results['backend_query']:
                self.log("  🔴 FAILURE LAYER: Backend - Cannot query the table")
            elif not self.results['api_response']:
                self.log("  🔴 FAILURE LAYER: API - Response format issues")
            elif not self.results['permissions_check']:
                self.log("  🔴 FAILURE LAYER: Permissions/RLS - Access restrictions")
            elif not self.results['frontend_receipt']:
                self.log("  🔴 FAILURE LAYER: Frontend - Cannot process API data")

        self.log("="*60)

        return {
            'status': status,
            'results': self.results,
            'errors': self.errors,
            'all_passed': all_passed
        }

def main():
    """Main execution function"""
    print("Transport Buses Table Connectivity Verifier")
    print("=" * 50)

    # Allow custom base URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    print(f"Testing against: {base_url}")

    verifier = TransportBusesVerifier(base_url)
    result = verifier.run_verification()

    # Exit with appropriate code
    sys.exit(0 if result['all_passed'] else 1)

if __name__ == "__main__":
    main()
