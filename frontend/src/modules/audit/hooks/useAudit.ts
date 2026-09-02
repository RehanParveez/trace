import { useQuery } from "@tanstack/react-query";
import { auditApi } from "../api/audit.api";
import type { AuditEntityType, AuditLogListParams } from "../types/audit.types";

export const auditKeys = {
  all: ["audit-log"] as const,
  list: (params: AuditLogListParams) => [...auditKeys.all, "list", params] as const,
  entity: (entityType: AuditEntityType, entityId: string) => [...auditKeys.all, "entity", entityType, entityId] as const,
};

export function useAuditLog(params: AuditLogListParams = {}) {
  return useQuery({
    queryKey: auditKeys.list(params),
    queryFn: () => auditApi.listAuditLog(params),
  });
}

export function useEntityAuditLog(entityType: AuditEntityType, entityId: string | undefined) {
  return useQuery({
    queryKey: auditKeys.entity(entityType, entityId ?? ""),
    queryFn: () => auditApi.listForEntity(entityType, entityId!),
    enabled: Boolean(entityId),
  });
}