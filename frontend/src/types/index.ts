export interface Scraper {
  id: number;
  name: string;
  description?: string;
  scraper_type: 'api' | 'web';
  module_path: string;
  class_name: string;
  config?: Record<string, any>;
  headers?: Record<string, string>;
  schema_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ScraperCreate {
  name: string;
  description?: string;
  scraper_type: 'api' | 'web';
  module_path: string;
  class_name: string;
  config?: Record<string, any>;
  headers?: Record<string, string>;
  is_active?: boolean;
}

export interface Job {
  id: number;
  scraper_id: number;
  name: string;
  description?: string;
  schedule_type: 'cron' | 'interval' | 'once';
  schedule_config: Record<string, any>;
  params?: Record<string, any>;
  is_active: boolean;
  last_run_at?: string;
  next_run_at?: string;
  scheduler_job_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface JobCreate {
  scraper_id: number;
  name: string;
  description?: string;
  schedule_type: 'cron' | 'interval' | 'once';
  schedule_config: Record<string, any>;
  params?: Record<string, any>;
  is_active?: boolean;
}

export interface Execution {
  id: number;
  scraper_id: number;
  job_id?: number;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  items_scraped: number;
  error_message?: string;
  logs?: string;
  params?: Record<string, any>;
  metrics?: Record<string, any>;
}

export interface ExecutionStats {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  running_executions: number;
  total_items_scraped: number;
  average_items_per_execution: number;
}

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
