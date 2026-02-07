import React, { useEffect, useState, useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import { format } from 'date-fns';

const ITEMS_PER_PAGE = 10;

const AttendanceManagement = () => {
  const [attendance, setAttendance] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [showMarkAttendanceModal, setShowMarkAttendanceModal] = useState(false);
  const [selectedStudents, setSelectedStudents] = useState({});
  const [studentMarks, setStudentMarks] = useState({});
  const [showMarks, setShowMarks] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    period: '1',
    subject: '',
    status: 'present',
    maxMarks: '10',
    examType: 'class_test' // Default exam type
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchAttendance = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build the base query
      const { data, error: queryError, count } = await supabase
        .from('attendance')
        .select(`
          id,
          date,
          status,
          period,
          subject,
          marked_time,
          marked_by,
          student_id,
          students!inner(
            id,
            name,
            branch,
            email
          )
        `, { count: 'exact' })
        .order('date', { ascending: false })
        .range(
          (currentPage - 1) * ITEMS_PER_PAGE,
          currentPage * ITEMS_PER_PAGE - 1
        );

      if (queryError) {
        console.error('Query error:', queryError);
        throw queryError;
      }

      console.log('Query successful. Records found:', data?.length || 0, 'Total count:', count);
      
      if (data && data.length > 0) {
        console.log('Sample record:', JSON.stringify(data[0], null, 2));
      }

      setAttendance(data || []);
      setTotalRecords(count || 0);
      
    } catch (err) {
      console.error('Error in fetchAttendance:', err);
      setError(err.message || 'Failed to fetch attendance data');
    } finally {
      setLoading(false);
    }
  }, [currentPage]);

  // Fetch students for attendance marking
  const fetchStudents = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('students')
        .select('id, name, branch, email')
        .order('name');

      if (error) throw error;

      // Initialize selected students with all set to present by default
      const initialSelected = {};
      data.forEach(student => {
        initialSelected[student.id] = 'present';
      });
      setSelectedStudents(initialSelected);
      setStudents(data || []);
    } catch (err) {
      console.error('Error fetching students:', err);
      setError('Failed to load student list');
    }
  }, []);

  // Initial fetch and refetch when dependencies change
  useEffect(() => {
    fetchAttendance();
    fetchStudents();
  }, [fetchAttendance, fetchStudents]);

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle student attendance status change
  const handleStudentStatusChange = (studentId, status) => {
    setSelectedStudents(prev => ({
      ...prev,
      [studentId]: status
    }));
  };

  // Handle marks change for a student
  const handleMarksChange = (studentId, marks) => {
    setStudentMarks(prev => ({
      ...prev,
      [studentId]: marks
    }));
  };

  // Handle form submission
  const handleSubmitAttendance = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
    
    try {
      setIsSubmitting(true);
      const { date, period, subject, maxMarks, examType } = formData;
      const currentUser = (await supabase.auth.getUser()).data.user;
      const currentDate = new Date().toISOString();
      
      // Prepare attendance records
      const attendanceRecords = Object.entries(selectedStudents)
        .filter(([_, status]) => status !== '') // Filter out unselected students
        .map(([studentId, status]) => ({
          student_id: studentId,
          date,
          period: parseInt(period, 10),
          subject,
          status,
          marked_by: currentUser?.email || 'admin',
          marked_time: currentDate
        }));

      // Start a transaction
      const { data, error: attendanceError } = await supabase.rpc('mark_attendance_with_marks', {
        attendance_records: attendanceRecords,
        marks_data: showMarks ? Object.entries(studentMarks)
          .filter(([studentId, marks]) => marks !== undefined && marks !== '')
          .map(([studentId, marks]) => ({
            student_id: studentId,
            subject,
            exam_type: examType,
            marks_obtained: parseFloat(marks) || 0,
            max_marks: parseFloat(maxMarks) || 10,
            date: currentDate,
            marked_by: currentUser?.email || 'admin'
          })) : []
      });

      if (attendanceError) throw attendanceError;

      // Refresh attendance data
      await fetchAttendance();
      setShowMarkAttendanceModal(false);
      
      // Show success message
      alert(showMarks ? 'Attendance and marks recorded successfully!' : 'Attendance marked successfully!');
    } catch (err) {
      console.error('Error marking attendance:', err);
      setError('Failed to mark attendance. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Calculate total pages
  const totalPages = Math.ceil(totalRecords / ITEMS_PER_PAGE);

  // Handle export to CSV
  const handleExportCSV = () => {
    const headers = ['Student Name', 'Student ID', 'Branch', 'Date', 'Period', 'Subject', 'Status', 'Marked Time', 'Marked By'];
    const csvContent = [
      headers.join(','),
      ...attendance.map(record => [
        `"${record.students?.name || 'N/A'}"`,
        `"${record.students?.student_id || 'N/A'}"`,
        `"${record.students?.branch || 'N/A'}"`,
        `"${new Date(record.date).toLocaleDateString()}"`,
        `"${record.period || 'N/A'}"`,
        `"${record.subject || 'N/A'}"`,
        `"${record.status?.toUpperCase() || 'N/A'}"`,
        `"${record.marked_time ? new Date(record.marked_time).toLocaleString() : 'N/A'}"`,
        `"${record.marked_by || 'N/A'}"`
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `attendance_${format(new Date(), 'yyyyMMdd')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Loading state
  if (loading && attendance.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
        <h1 className="text-2xl font-bold text-gray-800">Attendance Management</h1>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowMarkAttendanceModal(true)}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition-colors text-sm"
          >
            Mark Attendance
          </button>
          <button
            onClick={handleExportCSV}
            className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md transition-colors text-sm"
            disabled={attendance.length === 0}
          >
            Export to CSV
          </button>
        </div>
      </div>


      {/* Attendance Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Student</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Branch</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Period</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Marked At</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                  </td>
                </tr>
              ) : attendance.length > 0 ? (
                attendance.map((record) => (
                  <tr key={`${record.id}-${record.date}`} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-blue-600 font-medium">
                            {record.students?.name?.charAt(0).toUpperCase() || '?'}
                          </span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{record.students?.name || 'N/A'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.students?.student_id || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.students?.branch || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(record.date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.period || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.subject || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        record.status?.toLowerCase() === 'present' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {record.status?.toUpperCase() || 'UNKNOWN'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {record.marked_time ? new Date(record.marked_time).toLocaleString() : 'N/A'}
                      {record.marked_by && (
                        <div className="text-xs text-gray-400">by {record.marked_by}</div>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500">
                    No attendance records found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {(totalPages > 1 || currentPage > 1) && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className={`relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md ${
                  currentPage === 1 ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className={`ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md ${
                  currentPage === totalPages ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing <span className="font-medium">{(currentPage - 1) * ITEMS_PER_PAGE + 1}</span> to{' '}
                  <span className="font-medium">
                    {Math.min(currentPage * ITEMS_PER_PAGE, totalRecords)}
                  </span>{' '}
                  of <span className="font-medium">{totalRecords}</span> results
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <button
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                    className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    <span className="sr-only">First</span>
                    &laquo;
                  </button>
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className={`relative inline-flex items-center px-2 py-2 border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    <span className="sr-only">Previous</span>
                    &lsaquo;
                  </button>
                  
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    // Show first page, last page, current page, and pages around current page
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                          currentPage === pageNum 
                            ? 'z-10 bg-blue-50 border-blue-500 text-blue-600' 
                            : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className={`relative inline-flex items-center px-2 py-2 border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === totalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    <span className="sr-only">Next</span>
                    &rsaquo;
                  </button>
                  <button
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                    className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === totalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    <span className="sr-only">Last</span>
                    &raquo;
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mark Attendance Modal */}
      {showMarkAttendanceModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[80vh] flex flex-col">
            <div className="p-6 border-b">
              <h2 className="text-xl font-semibold">Mark Attendance</h2>
            </div>
            
            <form onSubmit={handleSubmitAttendance} className="flex-1 overflow-hidden flex flex-col">
              <div className="p-6 space-y-4 overflow-y-auto flex-1">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                    <input
                      type="date"
                      name="date"
                      value={formData.date}
                      onChange={handleInputChange}
                      className="w-full p-2 border rounded-md"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Period</label>
                    <select
                      name="period"
                      value={formData.period}
                      onChange={handleInputChange}
                      className="w-full p-2 border rounded-md"
                      required
                    >
                      {[1, 2, 3, 4, 5, 6, 7, 8].map(num => (
                        <option key={num} value={num}>Period {num}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                    <input
                      type="text"
                      name="subject"
                      value={formData.subject}
                      onChange={handleInputChange}
                      className="w-full p-2 border rounded-md"
                      placeholder="Enter subject name"
                      required
                    />
                  </div>
                  <div className="flex items-end space-x-2">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Record Marks?</label>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={showMarks}
                          onChange={() => setShowMarks(!showMarks)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        <span className="ml-3 text-sm font-medium text-gray-700">
                          {showMarks ? 'Yes' : 'No'}
                        </span>
                      </label>
                    </div>
                  </div>
                  
                  {showMarks && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Exam Type</label>
                        <select
                          name="examType"
                          value={formData.examType}
                          onChange={handleInputChange}
                          className="w-full p-2 border rounded-md"
                        >
                          <option value="class_test">Class Test</option>
                          <option value="unit_test">Unit Test</option>
                          <option value="mid_term">Mid Term</option>
                          <option value="final">Final Exam</option>
                          <option value="quiz">Quiz</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Max Marks</label>
                        <input
                          type="number"
                          name="maxMarks"
                          min="1"
                          step="0.01"
                          value={formData.maxMarks}
                          onChange={handleInputChange}
                          className="w-full p-2 border rounded-md"
                          placeholder="Enter max marks"
                        />
                      </div>
                    </>
                  )}
                  
                  <div className={showMarks ? 'col-span-2' : ''}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Default Status</label>
                    <select
                      name="status"
                      value={formData.status}
                      onChange={handleInputChange}
                      className="w-full p-2 border rounded-md"
                    >
                      <option value="present">Present</option>
                      <option value="absent">Absent</option>
                      <option value="late">Late</option>
                      <option value="excused">Excused</option>
                    </select>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Student</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Branch</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status{showMarks ? ' & Marks' : ''}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {students.map(student => (
                        <tr key={student.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                                <span className="text-blue-600 font-medium">
                                  {student.name?.charAt(0).toUpperCase() || '?'}
                                </span>
                              </div>
                              <div className="ml-4">
                                <div className="text-sm font-medium text-gray-900">{student.name}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {student.student_id || 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {student.branch || 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <select
                              value={selectedStudents[student.id] || 'present'}
                              onChange={(e) => handleStudentStatusChange(student.id, e.target.value)}
                              className="border rounded p-1 text-sm w-full mb-1"
                            >
                              <option value="present">Present</option>
                              <option value="absent">Absent</option>
                              <option value="late">Late</option>
                              <option value="excused">Excused</option>
                            </select>
                            {showMarks && (
                              <div className="mt-2">
                                <input
                                  type="number"
                                  min="0"
                                  step="0.01"
                                  max={formData.maxMarks || 10}
                                  value={studentMarks[student.id] || ''}
                                  onChange={(e) => handleMarksChange(student.id, e.target.value)}
                                  className="w-full p-1 border rounded text-sm"
                                  placeholder={`Marks (max ${formData.maxMarks || 10})`}
                                  disabled={selectedStudents[student.id] === 'absent'}
                                />
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="p-4 border-t bg-gray-50 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowMarkAttendanceModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Saving...' : 'Save Attendance'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AttendanceManagement;