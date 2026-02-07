import React, { useState, useEffect } from 'react';
import TransportService from '../../services/transportService';

const TransportDebug = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const testAPI = async () => {
      try {
        console.log('🔍 Testing transport API...');
        const result = await TransportService.getTransportStudents({ page: 1, limit: 5 });
        console.log('🔍 API Result:', result);
        
        setData(result);
        setLoading(false);
      } catch (err) {
        console.error('🔍 API Error:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    testAPI();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h2>Transport API Debug</h2>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};

export default TransportDebug;
