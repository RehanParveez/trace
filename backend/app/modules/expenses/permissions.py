from app.modules.identity.enums import PermissionKey

EXPENSE_PERMISSIONS = {
  PermissionKey.EXPENSE_READ: "View project expenses.",
  PermissionKey.EXPENSE_CREATE: "Record project expenses.",
  PermissionKey.EXPENSE_APPROVE: "Approve or reject project expenses.",
}