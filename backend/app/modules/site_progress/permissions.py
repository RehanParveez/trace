from app.modules.identity.enums import PermissionKey

SITE_PROGRESS_PERMISSIONS = {
  PermissionKey.SITE_LOG_READ: "View site progress logs.",
  PermissionKey.SITE_LOG_CREATE: "Create site progress logs.",
  PermissionKey.SITE_LOG_MANAGE: "Update and delete site progress logs.",
}