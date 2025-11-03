import axios from 'axios';
import type {
  Scraper,
  ScraperCreate,
  Job,
  JobCreate,
  Execution,
  ExecutionStats,
  PaginatedResponse,
} from '../types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
