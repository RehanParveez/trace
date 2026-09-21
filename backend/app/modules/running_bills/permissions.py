from app.modules.identity.enums import PermissionKey

RUNNING_BILL_PERMISSIONS = {
  PermissionKey.RUNNING_BILL_READ: "View running bills / IPCs for projects.",
  PermissionKey.RUNNING_BILL_CREATE: "Generate running bills from approved progress claims.",
  PermissionKey.RUNNING_BILL_ISSUE: "Issue or cancel running bills.",
}