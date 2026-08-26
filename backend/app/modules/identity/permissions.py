from app.modules.identity.enums import PermissionKey

IDENTITY_PERMISSIONS: dict[PermissionKey, str] = {
  PermissionKey.IDENTITY_READ:
    "View identity information.",

  PermissionKey.IDENTITY_MANAGE:
    "Manage identity information.",

  PermissionKey.ORGANIZATION_READ:
    "View organization information.",

  PermissionKey.ORGANIZATION_MANAGE:
    "Manage organization settings.",

  PermissionKey.ORGANIZATION_MEMBERS_MANAGE:
    "Manage organization members.",
}