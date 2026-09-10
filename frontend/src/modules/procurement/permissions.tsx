export const PROCUREMENT_PERMISSIONS = {
  PROCUREMENT_READ: "procurement:read",
  PROCUREMENT_CREATE: "procurement:create",
  PROCUREMENT_MANAGE: "procurement:manage",
} as const;

export type ProcurementPermission =
  (typeof PROCUREMENT_PERMISSIONS)[keyof typeof PROCUREMENT_PERMISSIONS];

export function hasProcurementPermission(
  permissions: string[] | undefined,
  permission: ProcurementPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}