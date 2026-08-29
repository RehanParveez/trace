export const PROJECT_PERMISSIONS = {
  PROJECT_READ: "project:read",
  PROJECT_CREATE: "project:create",
  PROJECT_UPDATE: "project:update",
  PROJECT_DELETE: "project:delete",
} as const;

export function hasProjectPermission(
  permissions: string[],
  permission: string,
): boolean {
  return permissions.includes(permission);
}