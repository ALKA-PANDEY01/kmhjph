const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API client for UK Wind Forecast backend
class APIError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

async function handleResponse(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || `HTTP error ${response.status}`,
      response.status
    );
  }
  return response.json();
}

export const api = {
  async getHealth() {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(response);
  },

  async getConfig() {
    const response = await fetch(`${API_BASE_URL}/api/config`);
    return handleResponse(response);
  },

  async getForecast(date) {
    const response = await fetch(`${API_BASE_URL}/api/forecast?date=${date}`);
    return handleResponse(response);
  },

  async getComparison(startDate, endDate) {
    const response = await fetch(
      `${API_BASE_URL}/api/comparison?start=${startDate}&end=${endDate}`
    );
    return handleResponse(response);
  },

  async getMetrics(startDate = null, endDate = null) {
    let url = `${API_BASE_URL}/api/metrics`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    return handleResponse(response);
  },

  async getErrorsByHour(startDate = null, endDate = null) {
    let url = `${API_BASE_URL}/api/errors/by-hour`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    return handleResponse(response);
  },

  async getErrorsDistribution(startDate = null, endDate = null) {
    let url = `${API_BASE_URL}/api/errors/distribution`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    return handleResponse(response);
  }
};

export { APIError };
