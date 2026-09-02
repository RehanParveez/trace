import { apiClient } from "../../../shared/api/client";
import type { AuditEntityType, AuditLogEntry, AuditLogListParams } from "../types/audit.types";

export const auditApi = {
  async listAuditLog(params: AuditLogListParams = {}): Promise<AuditLogEntry[]> {
    const response = await apiClient.get<AuditLogEntry[]>("/audit-log", {
      params: {
        entity_type: params.entityType, entity_id: params.entityId,
        actor_user_id: params.actorUserId, action: params.action,
        created_from: params.createdFrom, created_to: params.createdTo,
        skip: params.skip ?? 0, limit: params.limit ?? 100,
      },
    });
    return response.data;
  },

  async listForEntity(entityType: AuditEntityType, entityId: string): Promise<AuditLogEntry[]> {
    const response = await apiClient.get<AuditLogEntry[]>(`/audit-log/entity/${entityType}/${entityId}`);
    return response.data;
  },
};