export interface SiteLogEntry {
  id: string;
  project_id: string;
  log_date: string;
  workforce_count: number | null;
   weather: string | null;
  work_done: string | null;
  blockers: string | null;
  client_instructions: string | null;
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
  work_done?: string | null;
  blockers?: string | null;
  client_instructions?: string | null;
  notes?: string | null;
}

export interface SiteLogUpdateRequest {
  log_date?: string;
  workforce_count?: number | null;
  weather?: string | null;
  work_done?: string | null;
  blockers?: string | null;
  client_instructions?: string | null;
  notes?: string | null;
}

export interface SiteLogListParams {
  projectId?: string;
  skip?: number;
  limit?: number;
}

export interface DailyReport {
  project_id: string;
  project_name: string;
  report_date: string;
  logs: SiteLogEntry[];
  weather: string | null;
  work_done: string[];
  blockers: string[];
  client_instructions: string[];
  notes: string[];
  manpower_total: number | string;
  manpower: { trade: string; units: number | string }[];
  reported_workforce: number | null;
  manpower_mismatch: boolean;
  deliveries: { material_name: string; unit: string; quantity: number | string; supplier_name: string | null; invoice_number: string | null }[];
  issues: { material_name: string; unit: string; quantity: number | string; issue_type: string; issued_to: string | null }[];
  photos: { photo_id: string; photo_url: string; location_text: string | null; caption: string | null }[];
  photo_count: number;
}