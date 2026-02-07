#!/usr/bin/env python3
"""
Check and create missing transport tables in Supabase
"""

from supabase_client import get_supabase
import json

def check_tables():
    """Check existing tables and their structure"""
    supabase = get_supabase()
    
    tables_to_check = [
        'transport_students', 'transport_faculty', 'transport_buses', 
        'transport_drivers', 'transport_routes', 'transport_attendance',
        'transport_live_locations', 'transport_activities', 'transport_fee'
    ]
    
    existing_tables = []
    print('Checking transport tables:')
    for table in tables_to_check:
        try:
            # Try a simple select to see if table exists
            supabase.table(table).select('count', count='exact').limit(0).execute()
            print(f'  - {table}: EXISTS')
            existing_tables.append(table)
        except Exception:
            print(f'  - {table}: MISSING')
            
    return existing_tables

def create_missing_tables():
    """Create missing transport tables using RPC exec_sql"""
    supabase = get_supabase()

    try:
        sql_path = 'create_transport_tables.sql'
        if not os.path.exists(sql_path):
            # Try absolute path or search for it
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            sql_path = os.path.join(current_dir, 'create_transport_tables.sql')
        
        with open(sql_path, 'r') as f:
            sql = f.read()
            
        print('Executing SQL from create_transport_tables.sql...')
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        print('Database setup via SQL script completed!')
        
    except Exception as e:
        print(f'Error creating tables: {e}')

if __name__ == '__main__':
    print('Checking existing transport tables...')
    existing_tables = check_tables()
    print('\n' + '='*50)
    print('Creating missing tables and fixing schema...')
    create_missing_tables()
