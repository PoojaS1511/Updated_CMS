import React, { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import apiService from '../../services/api'
import LoadingSpinner from '../common/LoadingSpinner'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  AcademicCapIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'

const CourseManagement = () => {
  const [courses, setCourses] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editCourse, setEditCourse] = useState(null)
  const [formLoading, setFormLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue
  } = useForm()

  useEffect(() => {
    fetchCourses()
    fetchDepartments()
  }, [])

  const fetchCourses = async () => {
    try {
      const response = await apiService.getAllCourses()
      if (response.success) {
        setCourses(response.data)
      }
    } catch (error) {
      console.error('Error fetching courses:', error)
      // Fallback mock data
      setCourses([
        {
          id: 1,
          name: 'Bachelor of Technology - Computer Science Engineering',
          code: 'B.Tech CSE',
          department_id: 1,
          duration_years: 4,
          fee_per_semester: 60000,
          total_semesters: 8,
          departments: { name: 'Computer Science Engineering', code: 'CSE' }
        },
        {
          id: 2,
          name: 'Bachelor of Technology - Electronics and Communication Engineering',
          code: 'B.Tech ECE',
          department_id: 2,
          duration_years: 4,
          fee_per_semester: 55000,
          total_semesters: 8,
          departments: { name: 'Electronics and Communication Engineering', code: 'ECE' }
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const fetchDepartments = async () => {
    try {
      const response = await apiService.getAllDepartments()
      if (response.success) {
        setDepartments(response.data)
      }
    } catch (error) {
      console.error('Error fetching departments:', error)
      // Fallback mock data
      setDepartments([
        { id: 1, name: 'Computer Science Engineering', code: 'CSE' },
        { id: 2, name: 'Electronics and Communication Engineering', code: 'ECE' },
        { id: 3, name: 'Mechanical Engineering', code: 'MECH' }
      ])
    }
  }

  const handleAddCourse = () => {
    setEditCourse(null)
    reset()
    setShowForm(true)
  }

  const handleEditCourse = (course) => {
    setEditCourse(course)
    Object.keys(course).forEach(key => {
      setValue(key, course[key])
    })
    setShowForm(true)
  }

  const handleDeleteCourse = async (courseId) => {
    if (window.confirm('Are you sure you want to delete this course?')) {
      try {
        const response = await apiService.deleteCourse(courseId)
        if (response.success) {
          alert('Course deleted successfully!')
          fetchCourses()
        }
      } catch (error) {
        console.error('Error deleting course:', error)
        alert('Failed to delete course')
      }
    }
  }

  const onSubmit = async (data) => {
    setFormLoading(true)
    try {
      let response
      if (editCourse) {
        response = await apiService.updateCourse(editCourse.id, data)
      } else {
        response = await apiService.addCourse(data)
      }

      if (response.success) {
        alert(`Course ${editCourse ? 'updated' : 'added'} successfully!`)
        setShowForm(false)
        reset()
        fetchCourses()
      }
    } catch (error) {
      console.error('Error saving course:', error)
      alert(`Failed to ${editCourse ? 'update' : 'add'} course`)
    } finally {
      setFormLoading(false)
    }
  }

  const handleCloseForm = () => {
    setShowForm(false)
    setEditCourse(null)
    reset()
  }

  if (loading) {
    return <LoadingSpinner size="large" text="Loading courses..." />
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Course Management</h1>
              <p className="text-gray-600 mt-1">Manage courses and programs</p>
            </div>
            <button
              onClick={handleAddCourse}
              className="bg-royal-600 text-white px-4 py-2 rounded-md hover:bg-royal-700 flex items-center"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Add Course
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {courses.map((course) => (
                <tr key={course.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-royal-100 flex items-center justify-center">
                          <AcademicCapIcon className="h-6 w-6 text-royal-600" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {course.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {course.code}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {course.duration_years} Years
                    </div>
                    <div className="text-sm text-gray-500">
                      {course.total_semesters} Semesters
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleEditCourse(course)}
                        className="text-royal-600 hover:text-royal-900"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteCourse(course.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {courses.length === 0 && (
          <div className="text-center py-12">
            <AcademicCapIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No courses found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by adding a new course.
            </p>
          </div>
        )}
      </div>

      {/* Add/Edit Course Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-2/3 lg:w-1/2 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-gray-900">
                {editCourse ? 'Edit Course' : 'Add New Course'}
              </h3>
              <button
                onClick={handleCloseForm}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Course Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    {...register('name', { required: 'Course name is required' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-royal-500"
                    placeholder="e.g., Bachelor of Technology - Computer Science Engineering"
                  />
                  {errors.name && (
                    <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Course Code <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    {...register('code', { required: 'Course code is required' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-royal-500"
                    placeholder="e.g., B.Tech CSE"
                  />
                  {errors.code && (
                    <p className="mt-1 text-sm text-red-600">{errors.code.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Department <span className="text-red-500">*</span>
                  </label>
                  <select
                    {...register('department_id', { required: 'Department is required' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-royal-500"
                  >
                    <option value="">Select Department</option>
                    {departments.map(dept => (
                      <option key={dept.id} value={dept.id}>
                        {dept.name}
                      </option>
                    ))}
                  </select>
                  {errors.department_id && (
                    <p className="mt-1 text-sm text-red-600">{errors.department_id.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Duration (Years)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="6"
                    {...register('duration_years')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-royal-500"
                    defaultValue="4"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Total Semesters
                  </label>
                  <input
                    type="number"
                    min="2"
                    max="12"
                    {...register('total_semesters')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-royal-500"
                    defaultValue="8"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fee per Semester (₹)
                  </label>
                  <input
                    type="number"
                    min="0"
                    {...register('fee_per_semester')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-royal-500"
                    placeholder="50000"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-6 border-t">
                <button
                  type="button"
                  onClick={handleCloseForm}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-royal-600 text-white rounded-md hover:bg-royal-700 disabled:opacity-50"
                >
                  {formLoading ? (
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      {editCourse ? 'Updating...' : 'Adding...'}
                    </div>
                  ) : (
                    editCourse ? 'Update Course' : 'Add Course'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default CourseManagement
