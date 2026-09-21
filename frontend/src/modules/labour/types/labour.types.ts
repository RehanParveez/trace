export type LabourSourceType = "DIRECT" | "CONTRACTOR";
export type LabourDeploymentStatus = "ACTIVE" | "ENDED";

export interface LabourSource {
  id: string; name: string; source_type: LabourSourceType;
  contact_name: string | null; contact_phone: string | null; is_active: boolean; notes: string | null;
}

export interface LabourWorker {
  id: string; source_id: string; name: string; trade: string;
  cnic: string | null; phone: string | null; default_daily_rate: number | string | null; is_active: boolean;
}

export interface LabourDeployment {
  id: string; project_id: string; source_id: string; worker_id: string | null;
  trade: string; daily_rate: number | string; start_date: string; end_date: string | null;
  status: LabourDeploymentStatus;
}

export interface LabourAttendance {
  id: string; deployment_id: string; attendance_date: string; units_present: number | string; notes: string | null;
}

export interface LabourAdvance {
  id: string; source_id: string; worker_id: string | null;
  amount: number | string; advance_date: string; notes: string | null;
}

export interface LabourPayment {
  id: string; source_id: string; worker_id: string | null;
  period_start: string; period_end: string; gross_wage_amount: number | string;
  advance_recovered_amount: number | string; net_paid_amount: number | string;
  payment_date: string; notes: string | null;
}

export interface LabourTradeCost { trade: string; cost: number | string; }

export interface LabourSummary {
  project_id: string; period_start: string; period_end: string;
  total_accrued_cost: number | string; cost_by_trade: LabourTradeCost[];
  total_advances_given: number | string; total_payments_made: number | string;
  outstanding_advance_balance: number | string; currency: string;
}

export interface LabourCost { period_start: string; period_end: string; total_cost: number | string; currency: string; }
export interface LabourBalance { outstanding_advance_balance: number | string; currency: string; }
export interface DayAttendanceSummary { attendance_date: string; total_present: number | string; by_trade: LabourTradeCost[]; }