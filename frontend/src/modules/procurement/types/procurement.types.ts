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
  supplier_name: string | null;
  delivered_quantity: number | string;
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
  supplier_name?: string | null;
}

export interface ProcurementDelivery {
  id: string;
  request_id: string;
  project_id: string;
  material_name: string;
  unit: string;
  received_date: string;
  quantity: number | string;
  supplier_name: string | null;
  invoice_number: string | null;
  amount: number | string | null;
  notes: string | null;
  voided_at: string | null;
  void_reason: string | null;
  created_at: string;
}

export interface ProcurementDeliveryCreateRequest {
  received_date: string;
  quantity: number;
  supplier_name?: string | null;
  invoice_number?: string | null;
  amount?: number | null;
  notes?: string | null;
  allow_over_delivery?: boolean;
}

export interface ProcurementListParams {
  projectId?: string;
  status?: ProcurementStatus;
  page?: number;
  pageSize?: number;
}

export interface ProcurementOrganizationSummary {
  total_committed_amount: number | string;
  request_count: number;
}

export interface ProcurementStatusSummary {
  counts: Partial<Record<ProcurementStatus, number>>;
}

export interface ProcurementListResponse {
  items: ProcurementRequest[];
  total: number;
  page: number;
  page_size: number;
}