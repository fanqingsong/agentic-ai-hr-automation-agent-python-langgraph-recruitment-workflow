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

// Response interceptor: handle 401 errors (e.g. token expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('access_token');
      if (token) {
        localStorage.removeItem('access_token');
        // Redirect to login so user can sign in again
        window.location.replace('/login');
      }
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
  /** Candidate recommendations for this job (ranked by job evaluation workflow). refresh=true runs evaluation for all candidates. */
  getCandidateRecommendations: (jobId: string, refresh = false) =>
    api.get<{ total: number; rankings: { rank: number; candidate: any; score: number | null; reasoning?: string; tag?: string }[] }>(
      `/api/jobs/${jobId}/candidate-recommendations`,
      { params: { refresh: refresh ? '1' : '0' } }
    ),
};

// Candidates API
export const candidatesAPI = {
  list: (params?: any) => api.get('/api/candidates', { params }),
  get: (id: string) => api.get(`/api/candidates/${id}`),
  /** Export candidates. Pass FormData with optional job_id, format (csv|xlsx), min_score, max_score. */
  export: (formData: FormData) =>
    api.post('/api/export/candidates', formData, { responseType: 'blob' }),
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

// My Resumes API (job seeker: list and view own uploaded resumes)
export const myResumesAPI = {
  list: (params?: { limit?: number; skip?: number }) =>
    api.get<{ total: number; resumes: any[] }>('/api/my-resumes', { params }),
  get: (id: string) => api.get<any>(`/api/my-resumes/${id}`),
  /** Get download URL for attachment (same-origin with auth). Use downloadUrl from get() for preview. */
  downloadUrl: (id: string) => `${api.defaults.baseURL}/api/my-resumes/${id}/download`,
  /** Fetch file as blob (for programmatic download with auth). */
  downloadBlob: (id: string) => api.get(`/api/my-resumes/${id}/download`, { responseType: 'blob' }),
  /** Job recommendations for this resume (ranked by job evaluation workflow). refresh=true runs evaluation for all jobs. */
  getJobRecommendations: (resumeId: string, refresh = false) =>
    api.get<{ total: number; rankings: { rank: number; job: any; score: number | null; reasoning?: string; tag?: string }[] }>(
      `/api/my-resumes/${resumeId}/job-recommendations`,
      { params: { refresh: refresh ? '1' : '0' } }
    ),
};

export default api;
