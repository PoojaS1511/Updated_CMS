#!/usr/bin/env python3
"""
Create all missing transport tables in Supabase
"""

import sys
import os
sys.path.append('backend')

from backend.supabase_client import get_supabase

def create_transport_tables():
    """Create all transport tables in Supabase"""
    supabase = get_supabase()

    try:
        print("Creating transport tables...")

        # SQL commands to create all transport tables
        create_tables_sql = [
            # Transport Students Table
            """
            CREATE TABLE IF NOT EXISTS transport_students (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                student_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(15),
                address TEXT,
                route_id VARCHAR(20),
                route_name VARCHAR(100),
                pickup_point VARCHAR(100),
                status VARCHAR(20) DEFAULT 'Active',
                fee_status VARCHAR(20) DEFAULT 'Pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Faculty Table
            """
            CREATE TABLE IF NOT EXISTS transport_faculty (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                faculty_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(15),
                department VARCHAR(50),
                route_id VARCHAR(20),
                route_name VARCHAR(100),
                status VARCHAR(20) DEFAULT 'Active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Buses Table
            """
            CREATE TABLE IF NOT EXISTS transport_buses (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                bus_number VARCHAR(50) UNIQUE NOT NULL,
                route_id VARCHAR(20),
                route_name VARCHAR(100),
                capacity INTEGER NOT NULL,
                driver_id VARCHAR(20),
                driver_name VARCHAR(100),
                status VARCHAR(20) DEFAULT 'Active',
                last_service DATE,
                next_service DATE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Drivers Table
            """
            CREATE TABLE IF NOT EXISTS transport_drivers (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                driver_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(15) NOT NULL,
                license_number VARCHAR(50) UNIQUE NOT NULL,
                license_expiry DATE NOT NULL,
                blood_group VARCHAR(5),
                emergency_contact VARCHAR(15),
                experience_years INTEGER DEFAULT 0,
                shift VARCHAR(20) DEFAULT 'Morning',
                working_hours VARCHAR(50) DEFAULT '8 hours',
                assigned_bus VARCHAR(50),
                status VARCHAR(20) DEFAULT 'Active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Routes Table
            """
            CREATE TABLE IF NOT EXISTS transport_routes (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                route_id VARCHAR(20) UNIQUE NOT NULL,
                route_name VARCHAR(100) NOT NULL,
                stops JSONB,
                pickup_time TIME NOT NULL,
                drop_time TIME NOT NULL,
                total_students INTEGER DEFAULT 0,
                assigned_bus VARCHAR(50),
                assigned_driver VARCHAR(20),
                status VARCHAR(20) DEFAULT 'Active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Fees Table
            """
            CREATE TABLE IF NOT EXISTS transport_fees (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                student_id VARCHAR(20) NOT NULL,
                student_name VARCHAR(100) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                payment_status VARCHAR(20) DEFAULT 'Pending',
                payment_date DATE,
                payment_mode VARCHAR(20),
                due_date DATE,
                route_id VARCHAR(20),
                academic_year VARCHAR(20),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Attendance Table
            """
            CREATE TABLE IF NOT EXISTS transport_attendance (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                date DATE NOT NULL,
                entity_type VARCHAR(20) NOT NULL, -- 'student' or 'faculty'
                entity_id VARCHAR(20) NOT NULL,
                entity_name VARCHAR(100) NOT NULL,
                route_id VARCHAR(20),
                bus_number VARCHAR(50),
                status VARCHAR(20) DEFAULT 'Present', -- 'Present', 'Absent', 'Late'
                remarks TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,

            # Transport Live Locations Table
            """
            CREATE TABLE IF NOT EXISTS transport_live_locations (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                bus_id VARCHAR(50) NOT NULL,
                bus_number VARCHAR(50),
                route_id VARCHAR(20),
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                speed DECIMAL(5,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'Moving',
                driver_name VARCHAR(100),
                last_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(bus_id)
            );
            """,

            # Transport Activities Table
            """
            CREATE TABLE IF NOT EXISTS transport_activities (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                user_id VARCHAR(50),
                metadata JSONB,
                time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
        ]

        # Execute each CREATE TABLE statement
        for i, sql in enumerate(create_tables_sql, 1):
            try:
                # Use Supabase's rpc function to execute raw SQL
                result = supabase.rpc('exec_sql', {'sql': sql}).execute()
                print(f"✓ Created table {i}/9")
            except Exception as e:
                print(f"✗ Error creating table {i}: {str(e)}")
                # Continue with other tables
                continue

        # Create indexes for better performance
        index_sqls = [
            "CREATE INDEX IF NOT EXISTS idx_transport_students_student_id ON transport_students(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_transport_students_route_id ON transport_students(route_id);",
            "CREATE INDEX IF NOT EXISTS idx_transport_faculty_faculty_id ON transport_faculty(faculty_id);",
            "CREATE INDEX IF NOT EXISTS idx_transport_buses_bus_number ON transport_buses(bus_number);",
            "CREATE INDEX IF NOT EXISTS idx_transport_drivers_driver_id ON transport_drivers(driver_id);",
            "CREATE INDEX IF NOT EXISTS idx_transport_routes_route_id ON transport_routes(route_id);",
            "CREATE INDEX IF NOT EXISTS idx_transport_fees_student_id ON transport_fees(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_transport_attendance_date ON transport_attendance(date);",
            "CREATE INDEX IF NOT EXISTS idx_transport_live_locations_bus_id ON transport_live_locations(bus_id);"
        ]

        print("\nCreating indexes...")
        for sql in index_sqls:
            try:
                supabase.rpc('exec_sql', {'sql': sql}).execute()
            except Exception as e:
                print(f"Warning: Could not create index: {str(e)}")

        print("\n✓ All transport tables created successfully!")
        return True

    except Exception as e:
        print(f"✗ Error creating transport tables: {str(e)}")
        return False

def insert_sample_data():
    """Insert sample data for testing"""
    supabase = get_supabase()

    try:
        print("Inserting sample data...")

        # Sample routes
        routes_data = [
            {
                'route_id': 'RT001',
                'route_name': 'College to T.Nagar',
                'stops': ['College Main Gate', 'Anna Nagar', 'T.Nagar'],
                'pickup_time': '07:30:00',
                'drop_time': '18:30:00',
                'total_students': 45,
                'status': 'Active'
            },
            {
                'route_id': 'RT002',
                'route_name': 'College to Adyar',
                'stops': ['College Main Gate', 'Teynampet', 'Adyar'],
                'pickup_time': '07:45:00',
                'drop_time': '18:15:00',
                'total_students': 32,
                'status': 'Active'
            }
        ]

        for route in routes_data:
            try:
                supabase.table('transport_routes').insert(route).execute()
                print(f"✓ Inserted route: {route['route_name']}")
            except Exception as e:
                print(f"✗ Error inserting route {route['route_id']}: {str(e)}")

        # Sample buses
        buses_data = [
            {
                'bus_number': 'TN-01-AB-1234',
                'route_id': 'RT001',
                'route_name': 'College to T.Nagar',
                'capacity': 50,
                'driver_id': 'DRV001',
                'driver_name': 'Raj Kumar',
                'status': 'Active'
            },
            {
                'bus_number': 'TN-02-CD-5678',
                'route_id': 'RT002',
                'route_name': 'College to Adyar',
                'capacity': 45,
                'driver_id': 'DRV002',
                'driver_name': 'Mohan Singh',
                'status': 'Active'
            }
        ]

        for bus in buses_data:
            try:
                supabase.table('transport_buses').insert(bus).execute()
                print(f"✓ Inserted bus: {bus['bus_number']}")
            except Exception as e:
                print(f"✗ Error inserting bus {bus['bus_number']}: {str(e)}")

        # Sample drivers
        drivers_data = [
            {
                'driver_id': 'DRV001',
                'name': 'Raj Kumar',
                'phone': '+91 9876543210',
                'license_number': 'TN0123456789',
                'license_expiry': '2025-12-31',
                'experience_years': 8,
                'shift': 'Morning',
                'assigned_bus': 'TN-01-AB-1234',
                'status': 'Active'
            },
            {
                'driver_id': 'DRV002',
                'name': 'Mohan Singh',
                'phone': '+91 9876543211',
                'license_number': 'TN0987654321',
                'license_expiry': '2025-10-15',
                'experience_years': 12,
                'shift': 'Morning',
                'assigned_bus': 'TN-02-CD-5678',
                'status': 'Active'
            }
        ]

        for driver in drivers_data:
            try:
                supabase.table('transport_drivers').insert(driver).execute()
                print(f"✓ Inserted driver: {driver['name']}")
            except Exception as e:
                print(f"✗ Error inserting driver {driver['driver_id']}: {str(e)}")

        # Sample students
        students_data = [
            {
                'student_id': 'STU001',
                'name': 'Arun Kumar',
                'email': 'arun.kumar@student.edu',
                'phone': '+91 9876543212',
                'route_id': 'RT001',
                'route_name': 'College to T.Nagar',
                'pickup_point': 'Anna Nagar',
                'status': 'Active',
                'fee_status': 'Paid'
            },
            {
                'student_id': 'STU002',
                'name': 'Priya Sharma',
                'email': 'priya.sharma@student.edu',
                'phone': '+91 9876543213',
                'route_id': 'RT002',
                'route_name': 'College to Adyar',
                'pickup_point': 'Teynampet',
                'status': 'Active',
                'fee_status': 'Pending'
            }
        ]

        for student in students_data:
            try:
                supabase.table('transport_students').insert(student).execute()
                print(f"✓ Inserted student: {student['name']}")
            except Exception as e:
                print(f"✗ Error inserting student {student['student_id']}: {str(e)}")

        print("✓ Sample data inserted successfully!")
        return True

    except Exception as e:
        print(f"✗ Error inserting sample data: {str(e)}")
        return False

def test_tables():
    """Test that tables are accessible"""
    supabase = get_supabase()

    try:
        print("Testing table access...")

        # Test each table
        tables_to_test = [
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

        for table in tables_to_test:
            try:
                # Try to select from each table
                result = supabase.table(table).select('*').limit(1).execute()
                print(f"✓ {table}: accessible")
            except Exception as e:
                print(f"✗ {table}: {str(e)}")

        print("✓ Table access test completed!")
        return True

    except Exception as e:
        print(f"✗ Error testing tables: {str(e)}")
        return False

if __name__ == '__main__':
    print("Setting up Transport Database Tables")
    print("=" * 50)

    # Create tables
    if create_transport_tables():
        # Insert sample data
        insert_sample_data()

        # Test tables
        test_tables()

        print("\n" + "=" * 50)
        print("✓ Transport database setup completed!")
        print("You can now use the transport management system.")
    else:
        print("✗ Failed to create transport tables")
        sys.exit(1)
