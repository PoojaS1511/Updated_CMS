import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Container,
  TextField,
  Typography,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Grid,
  CircularProgress,
  Alert,
  Divider,
  Paper
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  Save as SaveIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import { feesService } from '../../services/feesService';

const NewFeeForm = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [students, setStudents] = useState([]);
  const [feeStructures, setFeeStructures] = useState([]);
  const [formData, setFormData] = useState({
    studentId: '',
    feeStructureId: '',
    amount: '',
    paymentMethod: 'cash',
    transactionId: '',
    academicYear: new Date().getFullYear(),
    semester: '1',
    notes: ''
  });
  
  // Update form data when fee structure changes
  useEffect(() => {
    if (formData.feeStructureId) {
      const selectedFee = feeStructures.find(fee => fee.id === formData.feeStructureId);
      if (selectedFee) {
        setFormData(prev => ({
          ...prev,
          amount: (selectedFee.amount || '').toString(),
          academicYear: selectedFee.academicYear || prev.academicYear,
          feeType: selectedFee.feeType
        }));
      }
    }
  }, [formData.feeStructureId, feeStructures]);

  // Fetch students and fee structures
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch students using the feesService
        const studentsData = await feesService.getStudents();
        
        // Get all fee structures with their actual IDs
        const allFees = await feesService.getAllFees();
        // Create a map of unique fee structures with their actual IDs
        const uniqueFeeStructures = [];
        const seen = new Set();
        
        allFees.forEach(fee => {
          if (fee.id && fee.feeType && fee.academicYear) {
            const key = `${fee.feeType}-${fee.academicYear}`;
            if (!seen.has(key)) {
              seen.add(key);
              uniqueFeeStructures.push({
                id: fee.id, // Use the actual UUID from the database
                name: `${fee.feeType} (${fee.academicYear})`,
                feeType: fee.feeType,
                academicYear: fee.academicYear,
                amount: fee.amount // Include the amount for pre-filling
              });
            }
          }
        });
        
        setStudents(studentsData || []);
        setFeeStructures(uniqueFeeStructures);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load required data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    console.log(`Form field changed - ${name}:`, value);
    
    // If fee structure is being changed, log the selected fee structure
    if (name === 'feeStructureId') {
      const selectedFee = feeStructures.find(fee => fee.id === value);
      console.log('Selected fee structure:', selectedFee);
    }
    
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      console.log('Form data before submission:', formData);
      
      // Validate required fields
      if (!formData.studentId) {
        throw new Error('Please select a student');
      }
      
      if (!formData.feeStructureId) {
        throw new Error('Please select a fee structure');
      }
      
      const selectedFee = feeStructures.find(fee => fee.id === formData.feeStructureId);
      if (!selectedFee) {
        throw new Error('Selected fee structure not found');
      }

      // Prepare payment data with proper types
      const paymentData = {
        student_id: formData.studentId,
        fee_structure_id: selectedFee.id, // Use the ID from the selected fee structure
        amount: parseFloat(formData.amount) || 0,
        payment_method: formData.paymentMethod || 'cash',
        transaction_id: formData.transactionId || `TXN-${Date.now()}`,
        fee_type: selectedFee.feeType || 'Tuition',
        academic_year: selectedFee.academicYear || new Date().getFullYear().toString(),
        semester: formData.semester || '1',
        status: 'paid',
        payment_date: new Date().toISOString(),
        notes: formData.notes || ''
      };
      
      console.log('Selected fee structure for payment:', selectedFee);

      console.log('Submitting payment with data:', paymentData);
      await feesService.recordPayment(paymentData);
      
      // Show success message and redirect
      navigate('/admin/fees', { 
        state: { 
          message: 'Fee payment recorded successfully!',
          severity: 'success'
        } 
      });
    } catch (err) {
      console.error('Error in handleSubmit:', {
        message: err.message,
        error: err,
        stack: err.stack
      });
      
      // Provide more user-friendly error messages
      let errorMessage = err.message || 'Failed to record payment';
      
      if (errorMessage.includes('violates foreign key constraint')) {
        errorMessage = 'Invalid student or fee structure reference. Please check the selected values.';
      } else if (errorMessage.includes('invalid input syntax')) {
        errorMessage = 'Invalid data format. Please check your input and try again.';
      } else if (errorMessage.includes('network')) {
        errorMessage = 'Network error. Please check your internet connection and try again.';
      } else if (errorMessage.includes('duplicate key')) {
        errorMessage = 'A payment with these details already exists.';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box mb={3}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(-1)}
          sx={{ mb: 2 }}
        >
          Back to Fees
        </Button>
        
        <Card>
          <CardHeader 
            title="Record New Fee Payment" 
            titleTypographyProps={{ variant: 'h5' }}
          />
          
          <CardContent>
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}
            
            <form onSubmit={handleSubmit}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth margin="normal" required>
                    <InputLabel>Student</InputLabel>
                    <Select
                      name="studentId"
                      value={formData.studentId}
                      onChange={handleChange}
                      label="Student"
                      required
                    >
                      {students.map((student) => (
                        <MenuItem key={student.id} value={student.id}>
                          {student.full_name} ({student.register_number})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth margin="normal" required>
                    <InputLabel>Fee Structure</InputLabel>
                    <Select
                      name="feeStructureId"
                      value={formData.feeStructureId}
                      onChange={handleChange}
                      label="Fee Structure"
                      required
                    >
                      {feeStructures.map((fee) => (
                        <MenuItem key={fee.id} value={fee.id}>
                          {fee.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    margin="normal"
                    label="Amount"
                    name="amount"
                    type="number"
                    value={formData.amount}
                    onChange={handleChange}
                    required
                    inputProps={{ min: 0, step: '0.01' }}
                  />
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth margin="normal" required>
                    <InputLabel>Payment Method</InputLabel>
                    <Select
                      name="paymentMethod"
                      value={formData.paymentMethod}
                      onChange={handleChange}
                      label="Payment Method"
                    >
                      <MenuItem value="cash">Cash</MenuItem>
                      <MenuItem value="card">Card</MenuItem>
                      <MenuItem value="bank_transfer">Bank Transfer</MenuItem>
                      <MenuItem value="upi">UPI</MenuItem>
                      <MenuItem value="other">Other</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    margin="normal"
                    label="Transaction ID (if any)"
                    name="transactionId"
                    value={formData.transactionId}
                    onChange={handleChange}
                  />
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    margin="normal"
                    label="Academic Year"
                    name="academicYear"
                    type="number"
                    value={formData.academicYear}
                    onChange={handleChange}
                    required
                  />
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth margin="normal" required>
                    <InputLabel>Semester</InputLabel>
                    <Select
                      name="semester"
                      value={formData.semester}
                      onChange={handleChange}
                      label="Semester"
                    >
                      {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
                        <MenuItem key={sem} value={sem.toString()}>
                          Semester {sem}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    margin="normal"
                    label="Notes"
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    multiline
                    rows={3}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Box display="flex" justifyContent="flex-end" gap={2} mt={3}>
                    <Button
                      variant="outlined"
                      startIcon={<CancelIcon />}
                      onClick={() => navigate('/admin/fees')}
                      disabled={loading}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="contained"
                      color="primary"
                      startIcon={<SaveIcon />}
                      disabled={loading}
                    >
                      {loading ? 'Saving...' : 'Save Payment'}
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </form>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default NewFeeForm;
