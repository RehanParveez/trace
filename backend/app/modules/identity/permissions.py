from app.modules.identity.enums import PermissionKey

IDENTITY_PERMISSIONS: dict[PermissionKey, str] = {
  PermissionKey.IDENTITY_READ:
    "View identity information.",

  PermissionKey.IDENTITY_MANAGE:
    "Manage identity information.",

}