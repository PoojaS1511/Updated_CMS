const express = require('express');
const router = express.Router();
const supabase = require('../supabase_client');

// Get student statistics
router.get('/stats', async (req, res) => {
  try {
    // Get total count directly from database
    const { count: totalCount, error: countError } = await supabase
      .from('students')
      .select('*', { count: 'exact', head: true });
    
    if (countError) throw countError;

    // Get gender distribution using a single query with grouping
    const { data: genderCounts, error: genderError } = await supabase
      .from('students')
      .select('gender', { count: 'exact' })
      .not('gender', 'is', null);
    
    if (genderError) throw genderError;

    // Count genders (case-insensitive)
    let maleCount = 0;
    let femaleCount = 0;
    let otherCount = 0;
    let notSpecified = 0;

    // First pass: count specified genders
    genderCounts.forEach(student => {
      if (!student.gender) {
        notSpecified++;
        return;
      }
      
      const gender = String(student.gender).toLowerCase().trim();
      if (gender === 'male') maleCount++;
      else if (gender === 'female') femaleCount++;
      else otherCount++;
    });

    // Get count of students with null/undefined gender
    const { count: nullGenderCount, error: nullError } = await supabase
      .from('students')
      .select('*', { count: 'exact', head: true })
      .or('gender.is.null,gender.eq.,gender.eq.undefined');
    
    if (nullError) throw nullError;
    
    notSpecified += nullGenderCount || 0;

    // Verify counts add up
    const calculatedTotal = maleCount + femaleCount + otherCount + notSpecified;
    if (calculatedTotal !== totalCount) {
      console.warn(`Count mismatch: total=${totalCount}, sum=${calculatedTotal}`);
      // If there's a discrepancy, trust the individual counts and update total
      totalCount = calculatedTotal;
    }

    res.json({
      status: 'success',
      data: {
        total: totalCount,
        male: maleCount,
        female: femaleCount,
        other: otherCount,
        notSpecified: notSpecified,
        lastUpdated: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('Error fetching student statistics:', error);
    res.status(500).json({ 
      status: 'error', 
      message: 'Failed to fetch student statistics',
      error: error.message 
    });
  }
});

// Get all students with pagination and filters
router.get('/', async (req, res) => {
  try {
    const { page = 1, limit = 10, search = '', ...filters } = req.query;
    const offset = (page - 1) * limit;

    // Build query
    let query = supabase
      .from('students')
      .select('*, courses(*)', { count: 'exact' });

    // Apply search
    if (search) {
      query = query.or(`first_name.ilike.%${search}%,last_name.ilike.%${search}%,email.ilike.%${search}%`);
    }

    // Apply filters
    Object.entries(filters).forEach(([key, value]) => {
      if (value) {
        query = query.eq(key, value);
      }
    });

    // Apply pagination
    query = query.range(offset, offset + limit - 1);

    const { data, error, count } = await query;

    if (error) throw error;

    res.json({
      status: 'success',
      data,
      pagination: {
        total: count,
        page: parseInt(page),
        limit: parseInt(limit),
        totalPages: Math.ceil(count / limit)
      }
    });
  } catch (error) {
    console.error('Error fetching students:', error);
    res.status(500).json({ status: 'error', message: 'Failed to fetch students' });
  }
});

// Get single student by ID
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const { data, error } = await supabase
      .from('students')
      .select('*, courses(*), fee_payments(*, fees(*))')
      .eq('id', id)
      .single();

    if (error) throw error;
    if (!data) {
      return res.status(404).json({ status: 'error', message: 'Student not found' });
    }

    res.json({ status: 'success', data });
  } catch (error) {
    console.error('Error fetching student:', error);
    res.status(500).json({ status: 'error', message: 'Failed to fetch student' });
  }
});

// Create new student
router.post('/', async (req, res) => {
  try {
    const studentData = req.body;
    
    const { data, error } = await supabase
      .from('students')
      .insert([studentData])
      .select()
      .single();

    if (error) throw error;

    res.status(201).json({ status: 'success', data });
  } catch (error) {
    console.error('Error creating student:', error);
    res.status(500).json({ status: 'error', message: 'Failed to create student' });
  }
});

// Update student
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const updates = req.body;
    
    const { data, error } = await supabase
      .from('students')
      .update(updates)
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    if (!data) {
      return res.status(404).json({ status: 'error', message: 'Student not found' });
    }

    res.json({ status: 'success', data });
  } catch (error) {
    console.error('Error updating student:', error);
    res.status(500).json({ status: 'error', message: 'Failed to update student' });
  }
});

// Delete student
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const { error } = await supabase
      .from('students')
      .delete()
      .eq('id', id);

    if (error) throw error;

    res.json({ status: 'success', message: 'Student deleted successfully' });
  } catch (error) {
    console.error('Error deleting student:', error);
    res.status(500).json({ status: 'error', message: 'Failed to delete student' });
  }
});

// Get student attendance
router.get('/:id/attendance', async (req, res) => {
  try {
    const { id } = req.params;
    const { start_date, end_date, subject_id } = req.query;
    
    let query = supabase
      .from('attendance')
      .select('*, subjects(*)')
      .eq('student_id', id);

    if (start_date && end_date) {
      query = query.gte('date', start_date).lte('date', end_date);
    }

    if (subject_id) {
      query = query.eq('subject_id', subject_id);
    }

    const { data, error } = await query;

    if (error) throw error;

    res.json({ status: 'success', data });
  } catch (error) {
    console.error('Error fetching student attendance:', error);
    res.status(500).json({ status: 'error', message: 'Failed to fetch attendance' });
  }
});

// Get student exam results
router.get('/:id/results', async (req, res) => {
  try {
    const { id } = req.params;
    
    const { data, error } = await supabase
      .from('exam_results')
      .select('*, exams(*, subjects(*))')
      .eq('student_id', id);

    if (error) throw error;

    res.json({ status: 'success', data });
  } catch (error) {
    console.error('Error fetching student results:', error);
    res.status(500).json({ status: 'error', message: 'Failed to fetch results' });
  }
});

module.exports = router;
