import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  FormControlLabel,
  Checkbox,
  Snackbar,
  Alert,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  CircularProgress
} from '@mui/material';
import { 
  Send as SendIcon, 
  CheckCircle as CheckCircleIcon,
  Email as EmailIcon,
  Sms as SmsIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { format } from 'date-fns';

// Sample notification data
const sampleNotifications = [
  {
    id: 1,
    title: 'Upcoming Parent-Teacher Meeting',
    message: 'Reminder: Parent-teacher meeting scheduled for August 15th at 2:00 PM.',
    type: 'email',
    recipient: 'All Parents',
    status: 'sent',
    date: '2025-08-10T10:30:00',
  },
  {
    id: 2,
    title: 'Fee Payment Due',
    message: 'Friendly reminder: Tuition fee for August is due on August 25th.',
    type: 'sms',
    recipient: 'All Students',
    status: 'scheduled',
    date: '2025-08-12T09:00:00',
  },
  {
    id: 3,
    title: 'Staff Meeting',
    message: 'Monthly staff meeting tomorrow at 3:00 PM in the conference room.',
    type: 'both',
    recipient: 'All Faculty',
    status: 'draft',
    date: new Date().toISOString(),
  },
];

const NotificationManagement = () => {
  const [formData, setFormData] = useState({
    title: '',
    message: '',
    recipientType: 'all',
    notificationType: 'email',
    isScheduled: false,
    scheduledTime: ''
  });
  const [notifications, setNotifications] = useState(sampleNotifications);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('compose'); // 'compose' or 'history'
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });

  const recipientTypes = [
    { value: 'all', label: 'All Users' },
    { value: 'students', label: 'Students Only' },
    { value: 'faculty', label: 'Faculty Only' },
    { value: 'parents', label: 'Parents Only' },
    { value: 'specific', label: 'Specific Users' }
  ];

  const notificationTypes = [
    { value: 'email', label: 'Email', icon: <EmailIcon fontSize="small" /> },
    { value: 'sms', label: 'SMS', icon: <SmsIcon fontSize="small" /> },
    { value: 'both', label: 'Both', icon: <>
        <EmailIcon fontSize="small" />
        <SmsIcon fontSize="small" />
      </> }
  ];

  const handleChange = (e) => {
    const { name, value, checked, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const newNotification = {
        id: Date.now(),
        title: formData.title,
        message: formData.message,
        type: formData.notificationType,
        recipient: recipientTypes.find(r => r.value === formData.recipientType)?.label || formData.recipientType,
        status: formData.isScheduled ? 'scheduled' : 'sent',
        date: formData.isScheduled ? formData.scheduledTime : new Date().toISOString(),
      };
      
      setNotifications([newNotification, ...notifications]);
      
      setSnackbar({
        open: true,
        message: formData.isScheduled 
          ? 'Notification scheduled successfully!'
          : 'Notification sent successfully!',
        severity: 'success'
      });
      
      // Reset form
      setFormData({
        title: '',
        message: '',
        recipientType: 'all',
        notificationType: 'email',
        isScheduled: false,
        scheduledTime: ''
      });
      
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to send notification. Please try again.',
        severity: 'error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteNotification = (id) => {
    setNotifications(notifications.filter(n => n.id !== id));
    setSnackbar({
      open: true,
      message: 'Notification deleted successfully!',
      severity: 'info'
    });
  };

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'sent': return 'success';
      case 'scheduled': return 'info';
      case 'draft': return 'warning';
      default: return 'default';
    }
  };

  const getTypeIcon = (type) => {
    switch(type) {
      case 'email': return <EmailIcon fontSize="small" />;
      case 'sms': return <SmsIcon fontSize="small" />;
      case 'both': return <><EmailIcon fontSize="small" /> <SmsIcon fontSize="small" /></>;
      default: return null;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Notification Center</Typography>
        <Box>
          <Button 
            variant={activeTab === 'compose' ? 'contained' : 'outlined'} 
            onClick={() => setActiveTab('compose')}
            sx={{ mr: 1 }}
          >
            Compose
          </Button>
          <Button 
            variant={activeTab === 'history' ? 'contained' : 'outlined'} 
            onClick={() => setActiveTab('history')}
          >
            Notification History
          </Button>
        </Box>
      </Box>
      
      {activeTab === 'compose' ? (
        <Card elevation={3}>
          <CardHeader 
            title="Compose New Notification" 
            titleTypographyProps={{ variant: 'h6' }}
          />
          <Divider />
          <CardContent>
            <form onSubmit={handleSubmit}>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Title"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    required
                    variant="outlined"
                    placeholder="Enter notification title"
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    multiline
                    rows={4}
                    variant="outlined"
                    placeholder="Type your message here..."
                  />
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth variant="outlined" required>
                    <InputLabel>Recipients</InputLabel>
                    <Select
                      name="recipientType"
                      value={formData.recipientType}
                      onChange={handleChange}
                      label="Recipients"
                    >
                      {recipientTypes.map((type) => (
                        <MenuItem key={type.value} value={type.value}>
                          {type.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth variant="outlined" required>
                    <InputLabel>Notification Type</InputLabel>
                    <Select
                      name="notificationType"
                      value={formData.notificationType}
                      onChange={handleChange}
                      label="Notification Type"
                    >
                      {notificationTypes.map((type) => (
                        <MenuItem key={type.value} value={type.value}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {type.icon}
                            {type.label}
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.isScheduled}
                        onChange={handleChange}
                        name="isScheduled"
                        color="primary"
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <ScheduleIcon color="action" sx={{ mr: 1 }} />
                        Schedule for later
                      </Box>
                    }
                  />
                  
                  {formData.isScheduled && (
                    <TextField
                      fullWidth
                      type="datetime-local"
                      name="scheduledTime"
                      value={formData.scheduledTime}
                      onChange={handleChange}
                      InputLabelProps={{
                        shrink: true,
                      }}
                      inputProps={{
                        min: new Date().toISOString().slice(0, 16)
                      }}
                      sx={{ mt: 2 }}
                      required
                    />
                  )}
                </Grid>
                
                <Grid item xs={12}>
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
                    startIcon={isLoading ? <CircularProgress size={24} /> : <SendIcon />}
                    disabled={isLoading}
                    fullWidth
                    size="large"
                  >
                    {isLoading 
                      ? 'Sending...' 
                      : formData.isScheduled 
                        ? 'Schedule Notification' 
                        : 'Send Notification Now'}
                  </Button>
                </Grid>
              </Grid>
            </form>
          </CardContent>
        </Card>
      ) : (
        <Card elevation={3}>
          <CardHeader 
            title="Notification History" 
            titleTypographyProps={{ variant: 'h6' }}
            subheader={`${notifications.length} total notifications`}
          />
          <Divider />
          <List sx={{ width: '100%', bgcolor: 'background.paper' }}>
            {notifications.length > 0 ? (
              notifications.map((notification) => (
                <React.Fragment key={notification.id}>
                  <ListItem alignItems="flex-start">
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {getTypeIcon(notification.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography component="span" variant="subtitle1" color="text.primary">
                            {notification.title}
                          </Typography>
                          <Chip 
                            label={notification.status}
                            size="small"
                            color={getStatusColor(notification.status)}
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography
                            component="span"
                            variant="body2"
                            color="text.primary"
                            display="block"
                            mb={1}
                          >
                            {notification.message}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                            <Chip 
                              icon={<EmailIcon fontSize="small" />}
                              label={`To: ${notification.recipient}`}
                              size="small"
                              variant="outlined"
                            />
                            <Chip 
                              icon={<ScheduleIcon fontSize="small" />}
                              label={format(new Date(notification.date), 'MMM d, yyyy h:mm a')}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                        </>
                      }
                    />
                    <ListItemSecondaryAction>
                      <IconButton 
                        edge="end" 
                        aria-label="delete"
                        onClick={() => handleDeleteNotification(notification.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                  <Divider component="li" />
                </React.Fragment>
              ))
            ) : (
              <ListItem>
                <ListItemText 
                  primary="No notifications found" 
                  primaryTypographyProps={{ textAlign: 'center', color: 'text.secondary', py: 4 }}
                />
              </ListItem>
            )}
          </List>
        </Card>
      )}
      
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default NotificationManagement;
