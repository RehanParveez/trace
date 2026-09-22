from app.modules.identity.enums import PermissionKey

SUBCONTRACTOR_PERMISSIONS = {
  PermissionKey.SUBCONTRACTOR_READ: "View subcontractors, agreements, bills and ledgers.",
  PermissionKey.SUBCONTRACTOR_MANAGE: "Manage subcontractors, agreements, and generate/issue/cancel bills.",
  PermissionKey.SUBCONTRACTOR_PAYMENT_MANAGE: "Record subcontractor advances and payments.",
}