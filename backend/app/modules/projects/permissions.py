from app.modules.identity.enums import PermissionKey

PROJECT_PERMISSIONS = {
  PermissionKey.PROJECT_READ:
    "View projects, clients, members, and milestones.",

  PermissionKey.PROJECT_CREATE:
    "Create projects and clients.",

  PermissionKey.PROJECT_UPDATE:
    "Update projects, clients, members, and milestones.",

  PermissionKey.PROJECT_DELETE:
    "Delete projects, clients, members, and milestones.",
}