#!/usr/bin/env python3
"""
Test transport database connection and tables
"""

import sys
import os
sys.path.append('backend')

from backend.supabase_client import get_supabase

def test_connection():
    """Test database connection"""
    try:
        supabase = get_supabase()
        print("✓ Supabase client initialized successfully")

        # Test connection with a simple query
        response = supabase.table('students').select('id').limit(1).execute()
        print("✓ Database connection successful")

        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def check_transport_tables():
    """Check if transport tables exist"""
    try:
        supabase = get_supabase()

        # Get all tables
        response = supabase.table('information_schema.tables').select('table_name').eq('table_schema', 'public').execute()
        all_tables = [row['table_name'] for row in response.data]

        transport_tables = [
            'transport_students',
            'transport_faculty',
            'transport_buses',
            'transport_drivers',
            'transport_routes',
            'transport_fees',
            'transport_attendance',
            'transport_live_locations',
            'transport_activities'
        ]

        print("\nTransport Tables Status:")
        print("-" * 40)

        existing_tables = []
        missing_tables = []

        for table in transport_tables:
            if table in all_tables:
                existing_tables.append(table)
                print(f"✓ {table}")
            else:
                missing_tables.append(table)
                print(f"✗ {table} (missing)")

        print(f"\nSummary: {len(existing_tables)}/{len(transport_tables)} tables exist")

        if missing_tables:
            print(f"Missing tables: {', '.join(missing_tables)}")

        return existing_tables, missing_tables

    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return [], transport_tables

if __name__ == '__main__':
    print("Testing Transport Database Setup")
    print("=" * 50)

    # Test connection
    if not test_connection():
        sys.exit(1)

    # Check tables
    existing, missing = check_transport_tables()

    if missing:
        print(f"\n⚠️  {len(missing)} transport tables are missing")
        print("Run the setup script to create them")
    else:
        print("\n✓ All transport tables exist")
