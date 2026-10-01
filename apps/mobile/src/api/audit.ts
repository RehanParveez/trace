import { authenticatedRequest } from "./client";
import type {AuditAction, AuditEntityType, AuditLogEntry, EntityActivitySummary,
} from "./types";

export type AuditListParams = {
  entity_type?: AuditEntityType;
  entity_id?: string;
  actor_user_id?: string;
  action?: AuditAction;
  created_from?: string;
  created_to?: string;
  skip?: number;
  limit?: number;
};

function buildQuery(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }

  const value = query.toString();
  return value ? `?${value}` : "";
}

export function listAuditLogs(
  params: AuditListParams = {},
): Promise<AuditLogEntry[]> {
  return authenticatedRequest<AuditLogEntry[]>(
    `/audit-log${buildQuery(params)}`,
  );
}

export function getLatestAuditByEntityType(
  entityType: AuditEntityType,
): Promise<EntityActivitySummary[]> {
  return authenticatedRequest<EntityActivitySummary[]>(
    `/audit-log/latest-by-entity-type${buildQuery({
      entity_type: entityType,
    })}`,
  );
}

export function listAuditLogForEntity(
  entityType: AuditEntityType,
  entityId: string,
): Promise<AuditLogEntry[]> {
  return authenticatedRequest<AuditLogEntry[]>(
    `/audit-log/entity/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
  );
}