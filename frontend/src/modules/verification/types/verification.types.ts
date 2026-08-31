export type ProgressClaimStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";

export interface ProgressClaim {
  id: string;
  organization_id: string;
  project_id: string;
  boq_item_id: string;
  claim_date: string;
  claimed_quantity: number | string;
  claimed_percentage: number | string;
  notes: string | null;
  status: ProgressClaimStatus;
  submitted_by: string | null;
  submitted_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProgressClaimCreateRequest {
  project_id: string;
  boq_item_id: string;
  claim_date: string;
  claimed_quantity: number;
  claimed_percentage: number;
  notes?: string | null;
}

export interface ProgressClaimUpdateRequest {
  version: number;
  claimed_quantity?: number;
  claimed_percentage?: number;
  claim_date?: string;
  notes?: string | null;
}

export interface ProgressClaimReviewRequest {
  version: number;
  note?: string | null;
}

export interface PhotoBOQLink {
  id: string;
  organization_id: string;
  project_id: string;
  progress_claim_id: string;
  site_photo_id: string;
  boq_item_id: string;
  note: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface PhotoBOQLinkCreateRequest {
  progress_claim_id: string;
  site_photo_id: string;
  boq_item_id: string;
  note?: string | null;
}