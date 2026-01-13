import axios from 'axios';
import type {
  Scraper,
  ScraperCreate,
  Job,
  JobCreate,
  Execution,
  ExecutionStats,
  PaginatedResponse,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  User,
  SystemStats,
} from '../types';

// Use relative URL to work with any protocol (HTTP/HTTPS) and hostname
// This is especially important when using Cloudflare tunnels or reverse proxies
const API_URL = process.env.REACT_APP_API_URL || '';

const client = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Scrapers
export const scraperApi = {
  list: async (skip = 0, limit = 100): Promise<PaginatedResponse<Scraper>> => {
    const response = await client.get('/scrapers', { params: { skip, limit } });
    return response.data;
  },

  get: async (id: number): Promise<Scraper> => {
    const response = await client.get(`/scrapers/${id}`);
    return response.data;
  },

  create: async (data: ScraperCreate): Promise<Scraper> => {
    const response = await client.post('/scrapers', data);
    return response.data;
  },

  update: async (id: number, data: Partial<ScraperCreate>): Promise<Scraper> => {
    const response = await client.put(`/scrapers/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/scrapers/${id}`);
  },

  run: async (id: number, params: Record<string, any> = {}): Promise<{ execution_id: number }> => {
    const response = await client.post(`/scrapers/${id}/run`, params);
    return response.data;
  },

  validate: async (modulePath: string, className: string): Promise<any> => {
    const response = await client.post('/scrapers/validate', null, {
      params: { module_path: modulePath, class_name: className },
    });
    return response.data;
  },
};

// Jobs
export const jobApi = {
  list: async (
    skip = 0,
    limit = 100,
    scraperId?: number,
    isActive?: boolean
  ): Promise<PaginatedResponse<Job>> => {
    const response = await client.get('/jobs', {
      params: { skip, limit, scraper_id: scraperId, is_active: isActive },
    });
    return response.data;
  },

  get: async (id: number): Promise<Job> => {
    const response = await client.get(`/jobs/${id}`);
    return response.data;
  },

  create: async (data: JobCreate): Promise<Job> => {
    const response = await client.post('/jobs', data);
    return response.data;
  },

  update: async (id: number, data: Partial<JobCreate>): Promise<Job> => {
    const response = await client.put(`/jobs/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/jobs/${id}`);
  },

  run: async (id: number): Promise<{ execution_id: number }> => {
    const response = await client.post(`/jobs/${id}/run`);
    return response.data;
  },
};

// Executions
export const executionApi = {
  list: async (
    skip = 0,
    limit = 100,
    scraperId?: number,
    jobId?: number,
    status?: string
  ): Promise<PaginatedResponse<Execution>> => {
    const response = await client.get('/executions', {
      params: { skip, limit, scraper_id: scraperId, job_id: jobId, status_filter: status },
    });
    return response.data;
  },

  get: async (id: number): Promise<Execution> => {
    const response = await client.get(`/executions/${id}`);
    return response.data;
  },

  getLogs: async (id: number): Promise<{ logs: string }> => {
    const response = await client.get(`/executions/${id}/logs`);
    return response.data;
  },

  getStats: async (scraperId?: number): Promise<ExecutionStats> => {
    const response = await client.get('/executions/stats', {
      params: { scraper_id: scraperId },
    });
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/executions/${id}`);
  },
};

// Authentication
export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await client.post('/auth/login', data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await client.post('/auth/register', data);
    return response.data;
  },

  me: async (): Promise<User> => {
    const response = await client.get('/auth/me');
    return response.data;
  },
};

// System
export const systemApi = {
  getStats: async (): Promise<SystemStats> => {
    const response = await client.get('/system/stats');
    return response.data;
  },
};
