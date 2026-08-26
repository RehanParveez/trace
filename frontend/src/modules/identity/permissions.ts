export const IDENTITY_PERMISSIONS = {
  IDENTITY_READ: "identity.read",
  IDENTITY_MANAGE: "identity.manage",
  ORGANIZATION_READ: "organization.read",
  ORGANIZATION_MANAGE: "organization.manage",
  ORGANIZATION_MEMBERS_MANAGE:
    "organization.members.manage",
} as const;

export type IdentityPermission =
  (typeof IDENTITY_PERMISSIONS)[keyof typeof IDENTITY_PERMISSIONS];

type PermissionUser = {
  role?: {
    permissions?: Array<{
      key: string;
    }>;
  };
};

export function hasPermission(
  user: PermissionUser | null | undefined,
  permission: string,
): boolean {
  return (
    user?.role?.permissions?.some(
      (item) => item.key === permission,
    ) ?? false
  );
}

export function hasAnyPermission(
  user: PermissionUser | null | undefined,
  permissions: string[],
): boolean {
  return permissions.some((permission) =>
    hasPermission(user, permission),
  );
}

export function hasAllPermissions(
  user: PermissionUser | null | undefined,
  permissions: string[],
): boolean {
  return permissions.every((permission) =>
    hasPermission(user, permission),
  );
}