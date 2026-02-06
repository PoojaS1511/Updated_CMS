import React, { useState, useEffect } from 'react';
import { useStudent } from '../../contexts/StudentContext';
import { CalendarIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { supabase } from '../../services/supabaseClient';
import { TABLES } from '../../lib/supabase';

// Mock data for development and testing
const mockAttendanceData = [
  {
    id: 1,
    date: '2025-02-05',
    status: 'present',
    subject: 'Mathematics',
    subjectCode: 'MATH101',
    period: 'Period 1 (09:00 - 10:00)',
    notes: 'Regular class'
  },
  {
    id: 2,
    date: '2025-02-05',
    status: 'present',
    subject: 'Physics',
    subjectCode: 'PHYS102',
    period: 'Period 2 (10:00 - 11:00)',
    notes: 'Lab session'
  },
  {
    id: 3,
    date: '2025-02-04',
    status: 'absent',
    subject: 'Chemistry',
    subjectCode: 'CHEM103',
    period: 'Period 3 (11:30 - 12:30)',
    notes: 'Missed class'
  },
  {
    id: 4,
    date: '2025-02-04',
    status: 'present',
    subject: 'Computer Science',
    subjectCode: 'CS104',
    period: 'Period 4 (13:30 - 14:30)',
    notes: 'Practical exam'
  },
  {
    id: 5,
    date: '2025-02-03',
    status: 'present',
    subject: 'Mathematics',
    subjectCode: 'MATH101',
    period: 'Period 1 (09:00 - 10:00)',
    notes: 'Quiz conducted'
  },
  {
    id: 6,
    date: '2025-02-03',
    status: 'late',
    subject: 'Physics',
    subjectCode: 'PHYS102',
    period: 'Period 2 (10:00 - 11:00)',
    notes: 'Arrived 15 minutes late'
  },
  {
    id: 7,
    date: '2025-02-02',
    status: 'present',
    subject: 'Chemistry',
    subjectCode: 'CHEM103',
    period: 'Period 3 (11:30 - 12:30)',
    notes: 'Lab experiment'
  },
  {
    id: 8,
    date: '2025-02-02',
    status: 'absent',
    subject: 'Computer Science',
    subjectCode: 'CS104',
    period: 'Period 4 (13:30 - 14:30)',
    notes: 'Medical leave'
  },
  {
    id: 9,
    date: '2025-02-01',
    status: 'present',
    subject: 'Mathematics',
    subjectCode: 'MATH101',
    period: 'Period 1 (09:00 - 10:00)',
    notes: 'Chapter test'
  },
  {
    id: 10,
    date: '2025-02-01',
    status: 'present',
    subject: 'Physics',
    subjectCode: 'PHYS102',
    period: 'Period 2 (10:00 - 11:00)',
    notes: 'Group discussion'
  }
];

const StudentAttendance = () => {
  const { student } = useStudent();
  const [attendanceData, setAttendanceData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAttendanceData = async () => {
      if (!student?.id) {
        console.log('No student ID available');
        // Use mock data in development when no student ID is available
        if (process.env.NODE_ENV === 'development') {
          console.log('Using mock attendance data for development');
          setAttendanceData(mockAttendanceData);
          setLoading(false);
        }
        return;
      }
      
      try {
        setLoading(true);
        console.log('Fetching student data for user ID:', student.id);
        
        // First, verify the student exists and get their details
        const { data: students, error: studentError, count } = await supabase
          .from(TABLES.STUDENTS)
          .select('id, course_id, current_semester, department_id, section, full_name, register_number', { count: 'exact' })
          .eq('user_id', student.id);

        console.log('Student query results:', { students, count, studentError });

        if (studentError) {
          console.error('Error fetching student data:', studentError);
          // Fall back to mock data in development
          if (process.env.NODE_ENV === 'development') {
            console.warn('Using mock data due to error:', studentError.message);
            setAttendanceData(mockAttendanceData);
            setLoading(false);
            return;
          }
          throw new Error(`Failed to load student data: ${studentError.message}`);
        }
        
        if (!students || students.length === 0) {
          const errorMsg = `No student record found for user ID: ${student.id}. Please ensure your student profile is properly set up.`;
          console.warn(errorMsg);
          // Fall back to mock data in development
          if (process.env.NODE_ENV === 'development') {
            console.warn('Using mock data as no student record found');
            setAttendanceData(mockAttendanceData);
            setLoading(false);
            return;
          }
          setError(errorMsg);
          setAttendanceData([]);
          return;
        }

        // Use the first student record if multiple exist
        const studentData = students[0];

        // Then fetch attendance records with related data
        const { data, error: fetchError } = await supabase
          .from('student_attendance')
          .select(`
            id,
            attendance_date,
            status,
            subject_id,
            subjects (id, name, code),
            class_schedule_id,
            class_schedules (id, period_number, start_time, end_time),
            notes
          `)
          .eq('student_id', student.id)
          .order('attendance_date', { ascending: false });

        if (fetchError) {
          console.error('Error fetching attendance data:', fetchError);
          // Fall back to mock data in development
          if (process.env.NODE_ENV === 'development') {
            console.warn('Using mock data due to fetch error:', fetchError.message);
            setAttendanceData(mockAttendanceData);
            setLoading(false);
            return;
          }
          throw fetchError;
        }

        // If no data found, use mock data in development
        if ((!data || data.length === 0) && process.env.NODE_ENV === 'development') {
          console.warn('No attendance records found, using mock data');
          setAttendanceData(mockAttendanceData);
          setLoading(false);
          return;
        }

        // Transform the data to match the expected format
        const formattedData = data.map(record => ({
          id: record.id,
          date: new Date(record.attendance_date).toISOString().split('T')[0],
          status: record.status.toLowerCase(),
          subject: record.subjects?.name || `Subject ${record.subject_id}`,
          subjectCode: record.subjects?.code || '',
          period: record.class_schedules 
            ? `Period ${record.class_schedules.period_number} (${record.class_schedules.start_time} - ${record.class_schedules.end_time})` 
            : 'N/A',
          notes: record.notes
        }));

        setAttendanceData(formattedData);
      } catch (err) {
        console.error('Error fetching attendance data:', err);
        // Fall back to mock data in development
        if (process.env.NODE_ENV === 'development') {
          console.warn('Using mock data due to error:', err.message);
          setAttendanceData(mockAttendanceData);
        } else {
          setError('Failed to load attendance data. ' + (err.message || 'Please try again later.'));
        }
      } finally {
        setLoading(false);
      }
    };

    fetchAttendanceData();
  }, [student?.id]);

  if (!student) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading student data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500 max-w-md p-4 bg-red-50 rounded-lg">
          <h3 className="font-bold">Error Loading Attendance</h3>
          <p className="mt-2">{error}</p>
          <p className="mt-2 text-sm">Please contact support if this issue persists.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading attendance data...</div>
      </div>
    );
  }

  // Error state is now handled above

  // Calculate attendance summary
  const totalClasses = attendanceData.length;
  const presentClasses = attendanceData.filter(record => record.status === 'present').length;
  const attendancePercentage = totalClasses > 0 ? Math.round((presentClasses / totalClasses) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Attendance</h1>
        
        {/* Attendance Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-center">
              <CalendarIcon className="h-6 w-6 text-blue-600 mr-2" />
              <h2 className="text-lg font-medium">Total Classes</h2>
            </div>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {totalClasses}
            </p>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="flex items-center">
              <CheckCircleIcon className="h-6 w-6 text-green-600 mr-2" />
              <h2 className="text-lg font-medium">Present</h2>
            </div>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {presentClasses} <span className="text-sm text-gray-500">({attendancePercentage}%)</span>
            </p>
          </div>
          
          <div className={`p-4 rounded-lg ${
            attendancePercentage >= 75 ? 'bg-green-50' : 
            attendancePercentage >= 50 ? 'bg-yellow-50' : 'bg-red-50'
          }`}>
            <div className="flex items-center">
              <ClockIcon className={`h-6 w-6 ${
                attendancePercentage >= 75 ? 'text-green-600' : 
                attendancePercentage >= 50 ? 'text-yellow-600' : 'text-red-600'
              } mr-2`} />
              <h2 className="text-lg font-medium">Attendance %</h2>
            </div>
            <p className={`text-3xl font-bold ${
              attendancePercentage >= 75 ? 'text-green-600' : 
              attendancePercentage >= 50 ? 'text-yellow-600' : 'text-red-600'
            } mt-2`}>
              {attendancePercentage}%
            </p>
          </div>
        </div>
        
        {/* Attendance Records */}
        <div className="overflow-x-auto">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Recent Attendance</h2>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subject
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Period
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {attendanceData.length > 0 ? (
                attendanceData.map((record) => (
                  <tr key={record.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(record.date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.subject}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        record.status === 'present' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {record.status.charAt(0).toUpperCase() + record.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.period}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-6 py-4 text-center text-sm text-gray-500">
                    No attendance records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default StudentAttendance;