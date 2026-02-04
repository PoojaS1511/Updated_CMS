import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';
import { 
  DocumentArrowDownIcon, 
  CalendarIcon, 
  ClockIcon,
  AcademicCapIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

const StudentExaminations = () => {
  const { user } = useAuth()
  const [examSchedule, setExamSchedule] = useState([])
  const [examResults, setExamResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('schedule') // schedule, results, hallticket

  useEffect(() => {
    fetchExamData()
  }, [user])

  const fetchExamData = async () => {
    try {
      if (!user) return

      // Mock exam schedule data
      const mockExamSchedule = [
        {
          id: 1,
          exam_name: 'Computer Networks IA1',
          exam_type: 'IA1',
          exam_date: '2025-02-15',
          exam_time: '10:00 AM',
          duration: '3 hours',
          room_number: 'CS-101',
          subjects: { name: 'Computer Networks', code: 'CS501', credits: 3 }
        },
        {
          id: 2,
          exam_name: 'Database Systems IA1',
          exam_type: 'IA1',
          exam_date: '2025-02-16',
          exam_time: '10:00 AM',
          duration: '3 hours',
          room_number: 'CS-102',
          subjects: { name: 'Database Management Systems', code: 'CS502', credits: 4 }
        },
        {
          id: 3,
          exam_name: 'Operating Systems IA2',
          exam_type: 'IA2',
          exam_date: '2025-03-15',
          exam_time: '2:00 PM',
          duration: '3 hours',
          room_number: 'CS-103',
          subjects: { name: 'Operating Systems', code: 'CS503', credits: 4 }
        },
        {
          id: 4,
          exam_name: 'Computer Networks Final',
          exam_type: 'final',
          exam_date: '2025-04-20',
          exam_time: '10:00 AM',
          duration: '3 hours',
          room_number: 'Main Hall',
          subjects: { name: 'Computer Networks', code: 'CS501', credits: 3 }
        }
      ]

      // Mock exam results data
      const mockExamResults = [
        {
          id: 1,
          exam_id: 1,
          marks_obtained: 85,
          max_marks: 100,
          grade: 'A',
          grade_points: 9.0,
          exam_type: 'IA1',
          subjects: { name: 'Computer Networks', code: 'CS501', credits: 3 }
        },
        {
          id: 2,
          exam_id: 2,
          marks_obtained: 78,
          max_marks: 100,
          grade: 'B+',
          grade_points: 8.0,
          exam_type: 'IA1',
          subjects: { name: 'Database Management Systems', code: 'CS502', credits: 4 }
        }
      ]

      setExamSchedule(mockExamSchedule)
      setExamResults(mockExamResults)

    } catch (error) {
      console.error('Error fetching exam data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getExamsByType = (type) => {
    return examResults.filter(result => result.exam_type === type)
  }

  const calculateGPA = (examType) => {
    const exams = getExamsByType(examType)
    if (exams.length === 0) return 0

    const totalCredits = exams.reduce((sum, exam) => sum + (exam.subjects?.credits || 0), 0)
    const totalPoints = exams.reduce((sum, exam) => {
      const percentage = (exam.marks_obtained / exam.max_marks) * 100
      const gradePoint = getGradePoint(percentage)
      return sum + (gradePoint * (exam.subjects?.credits || 0))
    }, 0)

    return totalCredits > 0 ? (totalPoints / totalCredits).toFixed(2) : 0
  }

  const getGradePoint = (percentage) => {
    if (percentage >= 90) return 10
    if (percentage >= 80) return 9
    if (percentage >= 70) return 8
    if (percentage >= 60) return 7
    if (percentage >= 50) return 6
    if (percentage >= 40) return 5
    return 0
  }

  const getGrade = (percentage) => {
    if (percentage >= 90) return 'A+'
    if (percentage >= 80) return 'A'
    if (percentage >= 70) return 'B+'
    if (percentage >= 60) return 'B'
    if (percentage >= 50) return 'C'
    if (percentage >= 40) return 'D'
    return 'F'
  }

  const downloadHallTicket = async (examId) => {
    // Don't proceed if already loading
    if (loading) return;

    try {
      if (!user) {
        toast.error('You must be logged in to download hall tickets');
        return;
      }

      // Get the student ID from the user object
      const studentId = user.id;

      // Show loading state
      setLoading(true);
      toast.info('Generating hall ticket...');

      console.log(`Generating hall ticket for student ${studentId}, exam ${examId}...`);

      // Call our backend API to get the hall ticket PDF
      // Pass student_id as query parameter for public access
      const apiUrl = `${import.meta.env.VITE_API_URL || API_URL.replace(/\/$/, '')}/student_dashboard/hall-ticket?exam_id=${examId}&student_id=${studentId}`;
      console.log('API URL:', apiUrl);

      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/pdf',
        }
      });

      if (!response.ok) {
        // Try to parse error as JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          console.error('Error response:', errorData);
          throw new Error(errorData.error || `Failed to generate hall ticket: HTTP ${response.status}`);
        } else {
          throw new Error(`Failed to generate hall ticket: HTTP ${response.status}`);
        }
      }

      // Get the PDF blob
      const blob = await response.blob();
      console.log('Hall ticket PDF received, size:', blob.size);

      // Create a URL for the blob
      const blobUrl = window.URL.createObjectURL(blob);

      // Create a temporary link element to trigger download
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `hall_ticket_${examId}.pdf`;

      // Append to body, click, and remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Also open in new tab for viewing
      window.open(blobUrl, '_blank');

      // Clean up the blob URL after a delay
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
      }, 100);

      toast.success('Hall ticket downloaded successfully!');

    } catch (error) {
      console.error('Error in downloadHallTicket:', error);
      
      // Handle specific error cases
      if (error.message.includes('401') || error.message.toLowerCase().includes('unauthorized')) {
        // Redirect to login if unauthorized
        window.location.href = '/login?session_expired=1&redirect=' + encodeURIComponent(window.location.pathname);
      } else if (error.message.includes('404') || error.message.toLowerCase().includes('not found')) {
        toast.error('The requested hall ticket was not found or is no longer available.');
      } else if (error.message.includes('500') || error.message.toLowerCase().includes('server')) {
        toast.error('A server error occurred. Please try again later or contact support if the problem persists.');
      } else {
        toast.error(error.message || 'Failed to download hall ticket. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-royal-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Examinations</h2>
        <p className="text-gray-600">Exam schedules, results, and hall ticket downloads</p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('schedule')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'schedule'
                  ? 'border-royal-500 text-royal-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Exam Schedule
            </button>
            <button
              onClick={() => setActiveTab('results')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'results'
                  ? 'border-royal-500 text-royal-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Results
            </button>
            <button
              onClick={() => setActiveTab('hallticket')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'hallticket'
                  ? 'border-royal-500 text-royal-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Hall Ticket
            </button>
          </nav>
        </div>

        <div className="p-6">
          {/* Exam Schedule Tab */}
          {activeTab === 'schedule' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Final Exam Schedule</h3>
                <span className="text-sm text-gray-600">Semester 5 • Academic Year 2024-25</span>
              </div>

              {examSchedule.length === 0 ? (
                <div className="text-center py-8">
                  <CalendarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No exam schedule available yet.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Time
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Subject
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Code
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Duration
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Hall
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {examSchedule.map((exam) => (
                        <tr key={exam.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {new Date(exam.exam_date).toLocaleDateString('en-US', {
                              weekday: 'short',
                              month: 'short',
                              day: 'numeric'
                            })}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {exam.start_time} - {exam.end_time}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {exam.subjects?.name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {exam.subjects?.code}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {exam.duration} hours
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {exam.hall_number}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Exam Instructions */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-900 mb-2">Exam Instructions:</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• Report to the exam hall 15 minutes before the scheduled time</li>
                  <li>• Bring your hall ticket and ID card</li>
                  <li>• Mobile phones and electronic devices are not allowed</li>
                  <li>• Use only blue/black pen for writing</li>
                  <li>• Follow all COVID-19 safety protocols</li>
                </ul>
              </div>
            </div>
          )}

          {/* Results Tab */}
          {activeTab === 'results' && (
            <div className="space-y-6">
              {/* GPA Summary */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-6 text-white">
                  <h4 className="text-sm font-medium opacity-90">IA1 GPA</h4>
                  <p className="text-2xl font-bold">{calculateGPA('IA1')}</p>
                </div>
                <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-lg p-6 text-white">
                  <h4 className="text-sm font-medium opacity-90">IA2 GPA</h4>
                  <p className="text-2xl font-bold">{calculateGPA('IA2')}</p>
                </div>
                <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-6 text-white">
                  <h4 className="text-sm font-medium opacity-90">Model GPA</h4>
                  <p className="text-2xl font-bold">{calculateGPA('MODEL')}</p>
                </div>
                <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg p-6 text-white">
                  <h4 className="text-sm font-medium opacity-90">Final GPA</h4>
                  <p className="text-2xl font-bold">{calculateGPA('FINAL')}</p>
                </div>
              </div>

              {/* Detailed Results */}
              {['IA1', 'IA2', 'MODEL', 'FINAL'].map((examType) => {
                const exams = getExamsByType(examType)
                if (exams.length === 0) return null

                return (
                  <div key={examType} className="border border-gray-200 rounded-lg p-6">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">
                      {examType} Results
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Subject
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Code
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Marks
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Percentage
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Grade
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Credits
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {exams.map((exam) => {
                            const percentage = ((exam.marks_obtained / exam.max_marks) * 100).toFixed(1)
                            const grade = getGrade(percentage)
                            return (
                              <tr key={exam.id}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                  {exam.subjects?.name}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                  {exam.subjects?.code}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {exam.marks_obtained}/{exam.max_marks}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {percentage}%
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                                    grade === 'A+' || grade === 'A' ? 'bg-green-500 text-white' :
                                    grade === 'B+' || grade === 'B' ? 'bg-blue-500 text-white' :
                                    grade === 'C' ? 'bg-yellow-500 text-white' :
                                    'bg-red-500 text-white'
                                  }`}>
                                    {grade}
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                  {exam.subjects?.credits}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Hall Ticket Tab */}
          {activeTab === 'hallticket' && (
            <div className="space-y-6">
              <div className="text-center">
                <AcademicCapIcon className="h-16 w-16 text-royal-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Hall Ticket Download</h3>
                <p className="text-gray-600 mb-6">
                  Download your hall ticket for the upcoming examinations
                </p>
                
                {console.log('Exam Schedule:', examSchedule)}
                
                {examSchedule && examSchedule.length > 0 ? (
                  <div className="space-y-4">
                    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">Available Hall Tickets</h4>
                      <ul className="space-y-4">
                        {examSchedule.map((exam) => (
                          <li key={exam.id} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-base font-medium text-gray-900">{exam.exam_name}</p>
                                <div className="mt-1 flex items-center text-sm text-gray-500">
                                  <CalendarIcon className="h-4 w-4 mr-1" />
                                  <span>{new Date(exam.exam_date).toLocaleDateString()}</span>
                                  <span className="mx-2">•</span>
                                  <ClockIcon className="h-4 w-4 mr-1" />
                                  <span>{exam.exam_time}</span>
                                  <span className="mx-2">•</span>
                                  <span>Room: {exam.room_number}</span>
                                </div>
                              </div>
                              <button
                                onClick={() => {
                                  console.log('Downloading hall ticket for exam:', exam);
                                  downloadHallTicket(exam.id);
                                }}
                                className="inline-flex items-center px-4 py-2 border border-black text-sm font-medium rounded-md shadow-sm text-white bg-black hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 transition-colors duration-200"
                              >
                                <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                                Download Hall Ticket
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" aria-hidden="true" />
                      </div>
                      <div className="ml-3">
                        <p className="text-sm text-yellow-700">
                          No upcoming exams found. Hall tickets will be available once the exam schedule is published.
                        </p>
                        <div className="mt-2">
                          <p className="text-xs text-yellow-600">
                            If you believe this is an error, please contact the examination department.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex">
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-yellow-800">Important Notes:</h4>
                    <ul className="mt-2 text-sm text-yellow-700 space-y-1">
                      <li>• Hall ticket will be available 1 week before exams</li>
                      <li>• Ensure all fee payments are completed</li>
                      <li>• Contact admin if you face any issues downloading</li>
                      <li>• Carry a printed copy to the examination hall</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default StudentExaminations
