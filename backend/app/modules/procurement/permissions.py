from app.modules.identity.enums import PermissionKey

PROCUREMENT_PERMISSIONS = {
  PermissionKey.PROCUREMENT_READ: "View procurement requests.",
  PermissionKey.PROCUREMENT_CREATE: "Create procurement requests.",
  PermissionKey.PROCUREMENT_MANAGE: "Approve, order, receive or cancel procurement requests.",
}