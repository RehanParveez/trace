export type SubcontractAgreementStatus = "ACTIVE" | "COMPLETED" | "TERMINATED";
export type SubcontractorBillStatus = "DRAFT" | "ISSUED" | "CANCELLED";

export interface Subcontractor {
  id: string; name: string; trade_specialization: string;
  contact_name: string | null; contact_phone: string | null; ntn_or_cnic: string | null;
  is_active: boolean; notes: string | null;
}

export interface AgreementItem { id: string; description: string; unit: string; quantity: number | string; rate: number | string; }

export interface SubcontractAgreement {
  id: string; project_id: string; subcontractor_id: string; scope_description: string;
  contract_value: number | string; default_retention_percentage: number | string;
  default_retention_cap_percentage: number | string | null;
  start_date: string; end_date: string | null; status: SubcontractAgreementStatus;
  notes: string | null; version: number;
}
export interface SubcontractAgreementDetail extends SubcontractAgreement { items: AgreementItem[]; }

export interface BillLineItem {
  id: string; agreement_item_id: string; description: string; unit: string;
  contract_quantity: number | string; rate: number | string;
  previous_percentage: number | string; cumulative_percentage: number | string;
  this_period_value: number | string; cumulative_value: number | string;
}

export interface SubcontractorBill {
  id: string; project_id: string; agreement_id: string; bill_number: number; status: SubcontractorBillStatus;
  period_start: string; period_end: string;
  gross_value_this_period: number | string; gross_value_cumulative: number | string;
  retention_percentage: number | string; retention_cap_percentage: number | string | null;
  retention_this_period: number | string; retention_cumulative: number | string;
  other_deductions_amount: number | string; other_deductions_note: string | null;
  net_payable: number | string; currency: string; notes: string | null;
  version: number; issued_at: string | null; created_at: string;
}
export interface SubcontractorBillDetail extends SubcontractorBill { line_items: BillLineItem[]; }

export interface SubcontractorAdvance { id: string; amount: number | string; advance_date: string; notes: string | null; }
export interface SubcontractorPayment {
  id: string; bill_id: string | null; gross_amount: number | string; advance_recovered_amount: number | string;
  net_paid_amount: number | string; payment_date: string; notes: string | null;
}

export interface SubcontractorLedger {
  agreement_id: string; contract_value: number | string; total_billed: number | string; total_paid: number | string;
  outstanding_bill_balance: number | string; total_advances_given: number | string;
  outstanding_advance_balance: number | string; currency: string;
}

export interface ProjectSubcontractCost { project_id: string; total_billed: number | string; currency: string; }