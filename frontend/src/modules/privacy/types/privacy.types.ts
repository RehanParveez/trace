export type SupportGrantStatus = "ACTIVE" | "EXPIRED" | "REVOKED";
export type ExportStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "EXPIRED";
export type DeletionStatus =
  | "PENDING"
  | "CANCELLED"
  | "EXECUTING"
  | "COMPLETED"
  | "FAILED";

export interface SupportGrant {
  id: string;
  reason: string;
  starts_at: string;
  expires_at: string;
  revoked_at: string | null;
  created_at: string;
  granted_by_user_id: string | null;
  status: SupportGrantStatus;
}

export interface SupportGrantCreateRequest {
  reason: string;
  hours: number;
}

export interface ExportJob {
  id: string;
  status: ExportStatus;
  size_bytes: number | null;
  table_count: number | null;
  row_count: number | null;
  file_count: number | null;
  error_message: string | null;
  created_at: string;
  finished_at: string | null;
  expires_at: string | null;
}

export interface ExportDownload {
  url: string;
  expires_in_seconds: number;
}

export interface DeletionRequest {
  id: string;
  status: DeletionStatus;
  reason: string | null;
  requested_at: string;
  scheduled_for: string;
  cancelled_at: string | null;
  error_message: string | null;
}

export interface DeletionRequestCreate {
  confirm_name: string;
  reason?: string | null;
}

export interface EncryptionStatus {
  enabled: boolean;
  provider: string;
  key_ready: boolean;
  fields: string[];
}

export interface PrivacyOverview {
  organization_name: string;
  encryption: EncryptionStatus;
  active_support_grant: SupportGrant | null;
  latest_export: ExportJob | null;
  pending_deletion: DeletionRequest | null;
  grace_days: number;
  support_grant_max_hours: number;
}
