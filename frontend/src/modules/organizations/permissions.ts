export const ORGANIZATION_PERMISSIONS = {
  ORGANIZATION_READ: "organization.read",
  ORGANIZATION_MANAGE: "organization.manage",
  ORGANIZATION_MEMBERS_MANAGE: "organization.members.manage",
} as const;

export type OrganizationPermission =
  (typeof ORGANIZATION_PERMISSIONS)[keyof typeof ORGANIZATION_PERMISSIONS];

export function hasOrganizationPermission(
  permissions: string[] | undefined,
  permission: OrganizationPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}