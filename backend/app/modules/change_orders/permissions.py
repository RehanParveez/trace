from app.modules.identity.enums import PermissionKey

CHANGE_ORDER_PERMISSIONS = {
  PermissionKey.CHANGE_ORDER_READ: "View change orders and their impact on project value.",
  PermissionKey.CHANGE_ORDER_CREATE: "Draft and cancel change orders.",
  PermissionKey.CHANGE_ORDER_APPROVE: "Approve or reject change orders, applying their value to the BOQ.",
}