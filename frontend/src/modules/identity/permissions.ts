export const IDENTITY_PERMISSIONS = {
  IDENTITY_READ: "identity.read",
  IDENTITY_MANAGE: "identity.manage",
  ORGANIZATION_READ: "organization.read",
  ORGANIZATION_MANAGE: "organization.manage",
  ORGANIZATION_MEMBERS_MANAGE: "organization.members.manage",
  ORGANIZATION_INVITATIONS_MANAGE: "organization.invitations.manage",
  PROJECT_READ: "project.read",
  PROJECT_CREATE: "project.create",
  PROJECT_UPDATE: "project.update",
  PROJECT_DELETE: "project.delete",
  SUBSCRIPTION_READ: "subscription.read",
  SUBSCRIPTION_MANAGE: "subscription.manage",
  SUBSCRIPTION_BILLING_MANAGE: "subscription.billing.manage",
  DRAWING_READ: "drawing:read",
  DRAWING_CREATE: "drawing:create",
  DRAWING_DELETE: "drawing:delete",
  BOQ_UPDATE: "boq:update",
  BOQ_APPROVE: "boq:approve",
  MATERIAL_LIBRARY_MANAGE: "material_library:manage",
  WHATSAPP_CHANNEL_MANAGE: "whatsapp.channel.manage",
  SITE_PHOTO_READ: "site_photo.read",
  SITE_PHOTO_MANAGE: "site_photo.manage",
  PROGRESS_CLAIM_READ: "progress_claim:read",
  PROGRESS_CLAIM_CREATE: "progress_claim:create",
  PROGRESS_CLAIM_UPDATE: "progress_claim:update",
  PROGRESS_CLAIM_SUBMIT: "progress_claim:submit",
  PROGRESS_CLAIM_REVIEW: "progress_claim:review",
  PHOTO_BOQ_LINK_READ: "photo_boq_link:read",
  PHOTO_BOQ_LINK_MANAGE: "photo_boq_link:manage",
  BOQ_ITEM_CREATE: "boq_item_create",
  BOQ_EXPORT: "boq_export",
  LABOUR_RATE_MANAGE: "labour_rate_manage",
  NOTIFICATION_READ: "notification:read",
  AUDIT_LOG_READ: "audit_log:read",
  AI_REQUEST_READ: "ai_request:read",
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