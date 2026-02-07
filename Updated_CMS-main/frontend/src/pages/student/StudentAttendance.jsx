import React from 'react';
import { useStudent } from '../../contexts/StudentContext';
import { CalendarIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';

const StudentAttendance = () => {
  const { student } = useStudent();

  // Sample attendance data - replace with actual data from your API
  const attendanceData = [
    { date: '2023-11-01', status: 'present', subject: 'Mathematics' },
    { date: '2023-11-02', status: 'absent', subject: 'Physics' },
    { date: '2023-11-03', status: 'present', subject: 'Chemistry' },
    { date: '2023-11-06', status: 'present', subject: 'Mathematics' },
    { date: '2023-11-07', status: 'absent', subject: 'Physics' },
  ];

  if (!student) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading attendance data...</div>
      </div>
    );
  }

  // Calculate attendance percentage
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
              {presentClasses}
            </p>
          </div>
          
          <div className="bg-amber-50 p-4 rounded-lg">
            <div className="flex items-center">
              <ClockIcon className="h-6 w-6 text-amber-600 mr-2" />
              <h2 className="text-lg font-medium">Attendance %</h2>
            </div>
            <div className="flex items-baseline mt-2">
              <p className="text-3xl font-bold text-gray-900">
                {attendancePercentage}
              </p>
              <span className="ml-2 text-sm text-gray-500">%</span>
            </div>
          </div>
        </div>

        {/* Attendance Table */}
        <div className="overflow-x-auto">
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
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {attendanceData.length > 0 ? (
                attendanceData.map((record, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(record.date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {record.subject}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        record.status === 'present' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {record.status === 'present' ? 'Present' : 'Absent'}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="3" className="px-6 py-4 text-center text-sm text-gray-500">
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
