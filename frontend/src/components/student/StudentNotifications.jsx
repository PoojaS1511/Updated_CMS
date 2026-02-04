import React, { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import apiService from '../../services/api'
import { 
  BellIcon, 
  ExclamationTriangleIcon, 
  InformationCircleIcon,
  CheckCircleIcon,
  XMarkIcon,
  FunnelIcon
} from '@heroicons/react/24/outline'

const StudentNotifications = () => {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, unread, academic, administrative, events

  useEffect(() => {
    fetchNotifications()
  }, [user])

  const fetchNotifications = async () => {
    try {
      if (!user) return

      // Mock notifications data
      const mockNotifications = [
        {
          id: 1,
          title: 'Semester Fee Payment Reminder',
          message: 'Your semester fee payment is due on January 15, 2025. Please complete the payment to avoid late fees.',
          type: 'administrative',
          priority: 'high',
          read: false,
          created_at: '2025-01-05T10:00:00Z',
          sender: 'Accounts Department'
        },
        {
          id: 2,
          title: 'Final Exam Schedule Released',
          message: 'The final examination schedule for Semester 5 has been published. Check your exam dates and timings.',
          type: 'academic',
          priority: 'high',
          read: false,
          created_at: '2025-01-04T14:30:00Z',
          sender: 'Examination Department'
        },
        {
          id: 3,
          title: 'Cultural Fest Registration Open',
          message: 'Registration for Cube Fiesta 2025 is now open. Register for various events and competitions.',
          type: 'events',
          priority: 'medium',
          read: true,
          created_at: '2025-01-03T09:15:00Z',
          sender: 'Student Activities'
        },
        {
          id: 4,
          title: 'Library Book Return Reminder',
          message: 'You have 2 books due for return by January 12, 2025. Please return them to avoid fine.',
          type: 'administrative',
          priority: 'medium',
          read: false,
          created_at: '2025-01-02T16:45:00Z',
          sender: 'Library Department'
        },
        {
          id: 5,
          title: 'Attendance Warning',
          message: 'Your attendance in Computer Networks is below 75%. Please attend classes regularly.',
          type: 'academic',
          priority: 'high',
          read: true,
          created_at: '2025-01-01T11:20:00Z',
          sender: 'Academic Department'
        },
        {
          id: 6,
          title: 'Hostel Room Inspection',
          message: 'Hostel room inspection will be conducted on January 8, 2025. Please keep your rooms clean.',
          type: 'administrative',
          priority: 'low',
          read: true,
          created_at: '2024-12-30T08:00:00Z',
          sender: 'Hostel Warden'
        },
        {
          id: 7,
          title: 'Project Submission Guidelines',
          message: 'Updated guidelines for semester project submission have been uploaded to the portal.',
          type: 'academic',
          priority: 'medium',
          read: false,
          created_at: '2024-12-28T13:30:00Z',
          sender: 'Dr. Smith - CSE Department'
        },
        {
          id: 8,
          title: 'Transport Route Change',
          message: 'Route RT-15 timing has been changed. New pickup time is 7:30 AM instead of 7:45 AM.',
          type: 'administrative',
          priority: 'medium',
          read: true,
          created_at: '2024-12-25T07:00:00Z',
          sender: 'Transport Department'
        }
      ]

      setNotifications(mockNotifications)
    } catch (error) {
      console.error('Error fetching notifications:', error)
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async (notificationId) => {
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === notificationId ? { ...notif, read: true } : notif
      )
    )
  }

  const markAllAsRead = () => {
    setNotifications(prev => 
      prev.map(notif => ({ ...notif, read: true }))
    )
  }

  const deleteNotification = (notificationId) => {
    setNotifications(prev => 
      prev.filter(notif => notif.id !== notificationId)
    )
  }

  const getFilteredNotifications = () => {
    let filtered = notifications

    switch (filter) {
      case 'unread':
        filtered = notifications.filter(notif => !notif.read)
        break
      case 'academic':
        filtered = notifications.filter(notif => notif.type === 'academic')
        break
      case 'administrative':
        filtered = notifications.filter(notif => notif.type === 'administrative')
        break
      case 'events':
        filtered = notifications.filter(notif => notif.type === 'events')
        break
      default:
        filtered = notifications
    }

    return filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  }

  const getNotificationIcon = (type, priority) => {
    if (priority === 'high') {
      return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
    }
    
    switch (type) {
      case 'academic':
        return <InformationCircleIcon className="h-5 w-5 text-blue-500" />
      case 'administrative':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'events':
        return <BellIcon className="h-5 w-5 text-purple-500" />
      default:
        return <InformationCircleIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getUnreadCount = () => {
    return notifications.filter(notif => !notif.read).length
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-royal-600"></div>
      </div>
    )
  }

  const filteredNotifications = getFilteredNotifications()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Notifications</h2>
            <p className="text-gray-600">
              {getUnreadCount()} unread notifications • {notifications.length} total
            </p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={markAllAsRead}
              className="px-4 py-2 bg-royal-600 text-white rounded-lg hover:bg-royal-700 transition-colors duration-200"
            >
              Mark All Read
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center space-x-4">
          <FunnelIcon className="h-5 w-5 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">Filter:</span>
          <div className="flex space-x-2">
            {[
              { key: 'all', label: 'All' },
              { key: 'unread', label: 'Unread' },
              { key: 'academic', label: 'Academic' },
              { key: 'administrative', label: 'Administrative' },
              { key: 'events', label: 'Events' }
            ].map(filterOption => (
              <button
                key={filterOption.key}
                onClick={() => setFilter(filterOption.key)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors duration-200 ${
                  filter === filterOption.key
                    ? 'bg-royal-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {filterOption.label}
                {filterOption.key === 'unread' && getUnreadCount() > 0 && (
                  <span className="ml-1 bg-red-500 text-white text-xs rounded-full px-1">
                    {getUnreadCount()}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className="bg-white rounded-lg shadow-md">
        {filteredNotifications.length === 0 ? (
          <div className="text-center py-12">
            <BellIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Notifications</h3>
            <p className="text-gray-600">
              {filter === 'all' 
                ? 'You have no notifications at the moment.' 
                : `No ${filter} notifications found.`}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredNotifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-6 hover:bg-gray-50 transition-colors duration-200 ${
                  !notification.read ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="flex-shrink-0 mt-1">
                      {getNotificationIcon(notification.type, notification.priority)}
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className={`text-lg font-semibold ${
                          !notification.read ? 'text-gray-900' : 'text-gray-700'
                        }`}>
                          {notification.title}
                        </h3>
                        {!notification.read && (
                          <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
                            New
                          </span>
                        )}
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          notification.priority === 'high' ? 'bg-red-100 text-red-800' :
                          notification.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {notification.priority}
                        </span>
                      </div>
                      
                      <p className="text-gray-600 mb-2">{notification.message}</p>
                      
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span>From: {notification.sender}</span>
                        <span>•</span>
                        <span>
                          {new Date(notification.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                        <span>•</span>
                        <span className="capitalize">{notification.type}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    {!notification.read && (
                      <button
                        onClick={() => markAsRead(notification.id)}
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        Mark Read
                      </button>
                    )}
                    <button
                      onClick={() => deleteNotification(notification.id)}
                      className="text-red-600 hover:text-red-700 p-1"
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Notification Settings */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Notification Preferences</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-gray-900">Email Notifications</h4>
              <p className="text-sm text-gray-600">Receive notifications via email</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-royal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-royal-600"></div>
            </label>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-gray-900">SMS Notifications</h4>
              <p className="text-sm text-gray-600">Receive important alerts via SMS</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-royal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-royal-600"></div>
            </label>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-gray-900">Push Notifications</h4>
              <p className="text-sm text-gray-600">Browser push notifications</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-royal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-royal-600"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  )
}

export default StudentNotifications
