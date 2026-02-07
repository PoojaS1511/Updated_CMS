const { createClient } = require('@supabase/supabase-js');

// Initialize Supabase client
const supabaseUrl = 'https://qkaaoeismqnhjyikgkme.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrYWFvZWlzbXFuaGp5aWtna21lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDMwMjU3NCwiZXhwIjoyMDY5ODc4NTc0fQ.L1ZCNGBbQqrRjCI9IrmounuEtwux4yBmhvPBR4vU5Uw';

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase configuration. Please check your .env file.');
}

const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
});

// Database tables
const TABLES = {
  USERS: 'users',
  STUDENTS: 'students',
  FACULTY: 'faculty',
  DEPARTMENTS: 'departments',
  COURSES: 'courses',
  STUDENT_COURSES: 'student_courses',
  SUBJECTS: 'subjects',
  EXAMS: 'exams',
  EXAM_RESULTS: 'exam_results',
  ATTENDANCE: 'attendance',
  FEES: 'fees',
  FEE_PAYMENTS: 'fee_payments',
  ADMISSION_APPLICATIONS: 'admission_applications'
};

// Utility functions for common database operations
const database = {
  // Fetch all records from a table
  fetchAll: async (table) => {
    const { data, error } = await supabase
      .from(table)
      .select('*');

    if (error) throw error;
    return data;
  },

  // Fetch a single record by ID
  fetchById: async (table, id) => {
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .eq('id', id)
      .single();

    if (error) throw error;
    return data;
  },

  // Insert a new record
  insert: async (table, record) => {
    const { data, error } = await supabase
      .from(table)
      .insert([record])
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  // Update a record
  update: async (table, id, updates) => {
    const { data, error } = await supabase
      .from(table)
      .update(updates)
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  // Delete a record
  delete: async (table, id) => {
    const { error } = await supabase
      .from(table)
      .delete()
      .eq('id', id);

    if (error) throw error;
    return true;
  },

  // Custom query
  query: async (table, queryFn) => {
    let query = supabase.from(table);
    query = queryFn(query);
    const { data, error } = await query;
    
    if (error) throw error;
    return data;
  }
};

module.exports = {
  supabase,
  TABLES,
  database
};
