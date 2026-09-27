export type BankGuaranteeHolderType = "CLIENT" | "SUBCONTRACTOR";
export type BankGuaranteeStatus = "ACTIVE" | "RENEWED" | "RELEASED" | "CALLED";

export interface BankGuarantee {
  id: string; project_id: string; holder_type: BankGuaranteeHolderType;
  boq_version_id: string | null; agreement_id: string | null;
  guarantee_number: string; issuing_bank: string;
  amount: number | string; currency: string;
  issue_date: string; expiry_date: string; status: BankGuaranteeStatus;
  released_at: string | null;
  superseded_at: string | null;
  renewed_from_guarantee_id: string | null;
  is_expired: boolean; is_expiring_soon: boolean;
  notes: string | null; created_at: string;
}

export interface ProjectBankGuaranteeSummary {
  project_id: string; active_count: number; expiring_soon_count: number;
  expired_count: number; total_active_value: number | string; currency: string;
}