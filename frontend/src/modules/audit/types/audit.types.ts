export type AuditEntityType =
  | "ORGANIZATION" | "ROLE" | "MEMBER" | "INVITATION" | "SUBSCRIPTION"
  | "PROJECT" | "BOQ_ITEM" | "DRAWING" | "PROGRESS_CLAIM"
  | "WHATSAPP_CHANNEL" | "MATERIAL_LIBRARY";

export type AuditAction = "CREATE" | "UPDATE" | "DELETE" | "APPROVE" | "REJECT" | "STATUS_CHANGE";

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  actor_name: string | null;
  actor_email: string | null;
  entity_type: AuditEntityType;
  entity_id: string | null;
  action: AuditAction;
  summary: string;
  changes: Record<string, { old: unknown; new: unknown }>;
  created_at: string;
}

export interface AuditLogListParams {
  entityType?: AuditEntityType;
  entityId?: string;
  actorUserId?: string;
  action?: AuditAction;
  createdFrom?: string;
  createdTo?: string;
  skip?: number;
  limit?: number;
}