export interface SiteLogEntry {
  id: string;
  project_id: string;
  log_date: string;
  workforce_count: number | null;
  weather: string | null;
  blockers: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SiteLogCreateRequest {
  project_id: string;
  log_date: string;
  workforce_count?: number | null;
  weather?: string | null;
  blockers?: string | null;
  notes?: string | null;
}

export interface SiteLogUpdateRequest {
  log_date?: string;
  workforce_count?: number | null;
  weather?: string | null;
  blockers?: string | null;
  notes?: string | null;
}

export interface SiteLogListParams {
  projectId?: string;
  skip?: number;
  limit?: number;
}