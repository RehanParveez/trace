export type RetentionHolderType = "CLIENT" | "SUBCONTRACTOR";

export interface RetentionRelease {
  id: string; project_id: string; holder_type: RetentionHolderType;
  boq_version_id: string | null; agreement_id: string | null;
  amount: number | string; release_date: string; notes: string | null; created_at: string;
}

export interface ClientRetentionLine {
  boq_version_id: string; boq_version_label: string;
  retention_held: number | string; retention_released: number | string; retention_outstanding: number | string;
}
export interface SubcontractorRetentionLine {
  agreement_id: string; subcontractor_name: string;
  retention_held: number | string; retention_released: number | string; retention_outstanding: number | string;
}
export interface ProjectRetentionSummary {
  project_id: string; client_lines: ClientRetentionLine[]; client_total_outstanding: number | string;
  subcontractor_lines: SubcontractorRetentionLine[]; subcontractor_total_outstanding: number | string; currency: string;
}
export interface OrganizationRetentionSummary {
  client_retention_held: number | string; subcontractor_retention_held: number | string; currency: string;
}