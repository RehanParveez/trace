export const AUDIT_PERMISSIONS = {
  AUDIT_LOG_READ: "audit_log:read",
} as const;

export type AuditPermission = (typeof AUDIT_PERMISSIONS)[keyof typeof AUDIT_PERMISSIONS];