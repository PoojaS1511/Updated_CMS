import React, { useState, useEffect } from 'react';
import TransportServiceNoAuth from '../../services/transportServiceNoAuth';

const TransportDebugNoAuth = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const testAPI = async () => {
      try {
        console.log('🔍 Testing transport API without auth...');
        const result = await TransportServiceNoAuth.getTransportStudents({ page: 1, limit: 5 });
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
      <h2>Transport API Debug (No Auth)</h2>
      <p>Success: {data?.success ? 'Yes' : 'No'}</p>
      <p>Data Count: {data?.data?.length || 0}</p>
      <p>Total: {data?.total || 'N/A'}</p>
      <pre style={{ background: '#f5f5f5', padding: '10px', maxHeight: '400px', overflow: 'auto' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
};

export default TransportDebugNoAuth;
