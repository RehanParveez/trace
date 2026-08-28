export const SUBSCRIPTION_PERMISSIONS = {
  SUBSCRIPTION_READ: "subscription:read",
  SUBSCRIPTION_MANAGE: "subscription:manage",
  SUBSCRIPTION_BILLING_MANAGE: "subscription:billing_manage",
} as const;

export function hasSubscriptionPermission(
  permissions: string[],
  permission: string,
): boolean {
  return permissions.includes(permission);
}