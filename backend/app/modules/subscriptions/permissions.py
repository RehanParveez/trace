from app.modules.identity.enums import PermissionKey

SUBSCRIPTION_PERMISSIONS = {
  PermissionKey.SUBSCRIPTION_READ:
    "View organization subscription and usage information.",

  PermissionKey.SUBSCRIPTION_MANAGE:
    "Manage organization subscription.",

  PermissionKey.SUBSCRIPTION_BILLING_MANAGE:
    "Manage organization billing information and subscription changes.",
}