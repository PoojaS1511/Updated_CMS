import { createClient } from '@supabase/supabase-js';

// Supabase configuration
const SUPABASE_URL = 'https://qkaaoeismqnhjyikgkme.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrYWFvZWlzbXFuaGp5aWtna21lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDI1NzQsImV4cCI6MjA2OTg3ODU3NH0.o3K8BNVZucbqFWsPzIZJ_H8_ApR3uu9Cvjm5C9HFKX0';
const SUPABASE_SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrYWFvZWlzbXFuaGp5aWtna21lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDMwMjU3NCwiZXhwIjoyMDY5ODc4NTc0fQ.L1ZCNGBbQqrRjCI9IrmounuEtwux4yBmhvPBR4vU5Uw';

// Initialize Supabase clients
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
export const supabaseAdmin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Table constants
export const TABLES = {
  USERS: 'users',
  STUDENTS: 'students',
  FACULTY: 'faculty',
  COURSES: 'courses',
  ATTENDANCE: 'attendance',
  EXAMS: 'exams',
  MARKS: 'marks',
  ANNOUNCEMENTS: 'announcements',
  FEES: 'fees',
  HOSTEL: 'hostel',
  MESS: 'mess',
  CLUBS: 'clubs',
  EVENTS: 'events',
  GRIEVANCES: 'grievances',
  LIBRARY: 'library',
  SPORTS: 'sports',
  MEDICAL: 'medical',
  IT_DIGITAL: 'it_digital',
  INFRASTRUCTURE: 'infrastructure',
  ACADEMIC_SUPPORT: 'academic_support',
  HEALTH_SAFETY: 'health_safety',
  CAREER_PREP: 'career_prep',
  ALUMNI: 'alumni',
  NOTIFICATIONS: 'notifications',
  POLLS: 'polls',
  POLL_OPTIONS: 'poll_options',
  SMART_CLASSROOM: 'smart_classroom',
  LAB_EQUIPMENT: 'lab_equipment',
  AUDITORIUM: 'auditorium',
  CLASSROOM: 'classroom',
  FACILITIES: 'facilities',
  INTERNSHIPS: 'internships',
  RELIEVING_REQUESTS: 'relieving_requests',
  ADMISSIONS: 'admissions',
  ACADEMIC: 'academic',
  QUALITY_AUDITS: 'quality_audits',
  ACCREDITATION: 'accreditation'
};

export default supabase;
