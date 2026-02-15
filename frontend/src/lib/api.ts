/**
 * Axios API client with authentication
 */

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data: { email: string; password: string; name: string; role: string }) =>
    api.post('/api/auth/register', data),

  login: (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    return api.post('/api/auth/token', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getCurrentUser: () => api.get('/api/auth/me'),

  updateCurrentUser: (data: any) => api.put('/api/auth/me', data),
};

// Jobs API
export const jobsAPI = {
  list: () => api.get('/api/jobs'),
  create: (data: any) => api.post('/api/jobs', data),
  get: (id: string) => api.get(`/api/jobs/${id}`),
  update: (id: string, data: any) => api.put(`/api/jobs/${id}`, data),
  delete: (id: string) => api.delete(`/api/jobs/${id}`),
};

// Candidates API
export const candidatesAPI = {
  list: (params?: any) => api.get('/api/candidates', { params }),
  get: (id: string) => api.get(`/api/candidates/${id}`),
  export: (data: any) => api.post('/api/export/candidates', data, { responseType: 'blob' }),
};

// Dashboard API
export const dashboardAPI = {
  getStats: (params?: any) => api.get('/api/dashboard/stats', { params }),
  getScoreDistribution: () => api.get('/api/analytics/score-distribution'),
};

// Batch Processing API
export const batchAPI = {
  process: (data: any) => api.post('/api/batch/process', data),
  processDirectory: (data: any) => api.post('/api/batch/process-directory', data),
  export: (batchId: string) => api.get(`/api/batch/${batchId}/export`, { responseType: 'blob' }),
};

export default api;
