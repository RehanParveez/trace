export type RunningBillStatus = "DRAFT" | "ISSUED" | "CANCELLED";

export interface RunningBillLineItem {
  id: string;
  boq_item_id: string;
  material_name: string;
  unit: string;
  contract_quantity: number | string;
  unit_rate: number | string;
  previous_percentage: number | string;
  cumulative_percentage: number | string;
  previous_quantity: number | string;
  cumulative_quantity: number | string;
  this_period_quantity: number | string;
  previous_value: number | string;
  cumulative_value: number | string;
  this_period_value: number | string;
}

export interface RunningBill {
  id: string;
  project_id: string;
  boq_version_id: string;
  bill_number: number;
  status: RunningBillStatus;
  period_start: string;
  period_end: string;
  gross_value_this_period: number | string;
  gross_value_cumulative: number | string;
  retention_percentage: number | string;
  retention_cap_percentage: number | string | null;
  retention_this_period: number | string;
  retention_cumulative: number | string;
  advance_recovery_amount: number | string;
  other_deductions_amount: number | string;
  other_deductions_note: string | null;
  net_payable: number | string;
  currency: string;
  notes: string | null;
  version: number;
  issued_at: string | null;
  created_at: string;
}

export interface RunningBillDetail extends RunningBill {
  line_items: RunningBillLineItem[];
}

export interface RunningBillCreateRequest {
  project_id: string;
  boq_version_id: string;
  period_start: string;
  period_end: string;
  retention_percentage?: number;
  retention_cap_percentage?: number | null;
  advance_recovery_amount?: number;
  other_deductions_amount?: number;
  other_deductions_note?: string | null;
  notes?: string | null;
}