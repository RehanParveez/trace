export const SITE_PROGRESS_PERMISSIONS = {
  SITE_LOG_READ: "site_log:read",
  SITE_LOG_CREATE: "site_log:create",
  SITE_LOG_MANAGE: "site_log:manage",
} as const;

export type SiteProgressPermission =
  (typeof SITE_PROGRESS_PERMISSIONS)[keyof typeof SITE_PROGRESS_PERMISSIONS];

export function hasSiteProgressPermission(
  permissions: string[] | undefined,
  permission: SiteProgressPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}