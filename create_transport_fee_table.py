import sqlite3
import uuid
from datetime import datetime, timedelta

# Database path
DB_PATH = 'Updated_CMS-main/backend/student_management.db'

def create_transport_fee_table():
    """Create transport_fee table with the specified schema"""
    print("Creating transport_fee table...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create transport_fee table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transport_fee (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            route_name TEXT,
            bus_no TEXT,
            fee_amount REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            due_amount REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'Pending',
            payment_date DATE,
            academic_year TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transport_fee_student_id ON transport_fee(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transport_fee_payment_status ON transport_fee(payment_status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transport_fee_academic_year ON transport_fee(academic_year)')

    print("✅ transport_fee table created successfully")

    # Insert sample data
    print("Inserting sample transport fee data...")

    sample_data = [
        {
            'id': str(uuid.uuid4()),
            'student_id': '2024001',
            'route_name': 'Route A - City Center',
            'bus_no': 'BUS001',
            'fee_amount': 2500.00,
            'paid_amount': 2500.00,
            'due_amount': 0.00,
            'payment_status': 'Paid',
            'payment_date': '2024-08-15',
            'academic_year': '2024-25',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'student_id': '2024002',
            'route_name': 'Route B - Suburban',
            'bus_no': 'BUS002',
            'fee_amount': 3000.00,
            'paid_amount': 1500.00,
            'due_amount': 1500.00,
            'payment_status': 'Pending',
            'payment_date': None,
            'academic_year': '2024-25',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'student_id': '2024003',
            'route_name': 'Route C - Rural',
            'bus_no': 'BUS003',
            'fee_amount': 2000.00,
            'paid_amount': 0.00,
            'due_amount': 2000.00,
            'payment_status': 'Overdue',
            'payment_date': None,
            'academic_year': '2024-25',
            'created_at': (datetime.now() - timedelta(days=30)).isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'student_id': '2024004',
            'route_name': 'Route A - City Center',
            'bus_no': 'BUS001',
            'fee_amount': 2500.00,
            'paid_amount': 2000.00,
            'due_amount': 500.00,
            'payment_status': 'Partial',
            'payment_date': '2024-09-01',
            'academic_year': '2024-25',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'student_id': '2024005',
            'route_name': 'Route B - Suburban',
            'bus_no': 'BUS002',
            'fee_amount': 3000.00,
            'paid_amount': 3000.00,
            'due_amount': 0.00,
            'payment_status': 'Paid',
            'payment_date': '2024-07-20',
            'academic_year': '2024-25',
            'created_at': datetime.now().isoformat()
        }
    ]

    # Insert sample data
    for record in sample_data:
        cursor.execute('''
            INSERT INTO transport_fee
            (id, student_id, route_name, bus_no, fee_amount, paid_amount,
             due_amount, payment_status, payment_date, academic_year, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record['id'], record['student_id'], record['route_name'], record['bus_no'],
            record['fee_amount'], record['paid_amount'], record['due_amount'],
            record['payment_status'], record['payment_date'], record['academic_year'],
            record['created_at']
        ))

    conn.commit()
    print(f"✅ Inserted {len(sample_data)} sample records")

    # Verify the data
    cursor.execute("SELECT COUNT(*) FROM transport_fee")
    count = cursor.fetchone()[0]
    print(f"✅ Total records in transport_fee table: {count}")

    # Show sample records
    cursor.execute("SELECT * FROM transport_fee LIMIT 3")
    sample_records = cursor.fetchall()
    print("\n📝 Sample records:")
    for i, record in enumerate(sample_records, 1):
        print(f"  Record {i}: {record}")

    conn.close()
    print("✅ transport_fee table setup completed successfully")

if __name__ == "__main__":
    create_transport_fee_table()
