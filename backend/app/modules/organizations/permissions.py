from app.modules.identity.enums import PermissionKey

ORGANIZATION_PERMISSIONS = {
  PermissionKey.ORGANIZATION_READ:
    "View organization information.",

  PermissionKey.ORGANIZATION_MANAGE:
    "Manage organization settings.",

  PermissionKey.ORGANIZATION_MEMBERS_MANAGE:
    "Manage organization members.",
}