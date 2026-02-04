const express = require('express');
const router = express.Router();
const { supabase } = require('../supabase_client');

// Get all clubs
router.get('/', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('clubs')
      .select('*')
      .order('name', { ascending: true });

    if (error) throw error;
    res.json(data);
  } catch (error) {
    console.error('Error fetching clubs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get club by ID
router.get('/:id', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('clubs')
      .select('*')
      .eq('id', req.params.id)
      .single();

    if (error) throw error;
    if (!data) return res.status(404).json({ error: 'Club not found' });
    
    res.json(data);
  } catch (error) {
    console.error('Error fetching club:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create a new club
router.post('/', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('clubs')
      .insert([req.body])
      .select()
      .single();

    if (error) throw error;
    res.status(201).json(data);
  } catch (error) {
    console.error('Error creating club:', error);
    res.status(400).json({ error: error.message });
  }
});

// Update a club
router.put('/:id', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('clubs')
      .update(req.body)
      .eq('id', req.params.id)
      .select()
      .single();

    if (error) throw error;
    if (!data) return res.status(404).json({ error: 'Club not found' });
    
    res.json(data);
  } catch (error) {
    console.error('Error updating club:', error);
    res.status(400).json({ error: error.message });
  }
});

// Delete a club
router.delete('/:id', async (req, res) => {
  try {
    const { error } = await supabase
      .from('clubs')
      .delete()
      .eq('id', req.params.id);

    if (error) throw error;
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting club:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
