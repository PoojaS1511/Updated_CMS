import axios from 'axios';

// Create a simple HTTP client without authentication for transport APIs
const transportHttpClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

class TransportServiceNoAuth {
  static async getTransportStudents(filters = {}) {
    try {
      const queryString = new URLSearchParams(filters).toString();
      const endpoint = `/transport/students${queryString ? '?' + queryString : ''}`;
      console.log('🔍 Making request to:', endpoint);
      const response = await transportHttpClient.get(endpoint);
      console.log('🔍 Response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error fetching transport students:', error);
      return { success: false, error: error.message };
    }
  }
}

export default TransportServiceNoAuth;
