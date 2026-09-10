export type ProcurementStatus = "REQUESTED" | "APPROVED" | "ORDERED" | "RECEIVED" | "CANCELLED";

export interface ProcurementRequest {
  id: string;
  project_id: string;
  material_name: string;
  quantity: number | string;
  unit: string;
  estimated_amount: number | string | null;
  status: ProcurementStatus;
  needed_by_date: string | null;
  notes: string | null;
  requested_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProcurementCreateRequest {
  project_id: string;
  material_name: string;
  quantity: number;
  unit: string;
  estimated_amount?: number | null;
  needed_by_date?: string | null;
  notes?: string | null;
}

export interface ProcurementStatusUpdateRequest {
  status: ProcurementStatus;
}

export interface ProcurementListParams {
  projectId?: string;
  status?: ProcurementStatus;
  skip?: number;
  limit?: number;
}