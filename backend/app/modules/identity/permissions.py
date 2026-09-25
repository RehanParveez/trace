from app.modules.identity.enums import PermissionKey

IDENTITY_PERMISSIONS: dict[PermissionKey, str] = {
  PermissionKey.IDENTITY_READ: "View identity information.",
  PermissionKey.IDENTITY_MANAGE: "Manage identity information.",
  PermissionKey.ORGANIZATION_READ: "View organization information.",
  PermissionKey.ORGANIZATION_MANAGE: "Manage organization settings.",
  PermissionKey.ORGANIZATION_MEMBERS_MANAGE: "Manage organization members.",
  PermissionKey.ORGANIZATION_INVITATIONS_MANAGE: "Invite, view, and revoke organization invitations.",
  PermissionKey.BUDGET_READ: "View project budgets and category allocations.",
  PermissionKey.BUDGET_MANAGE: "Create and update project budgets.",
  PermissionKey.EXPENSE_READ: "View project expenses.",
  PermissionKey.EXPENSE_CREATE: "Record project expenses.",
  PermissionKey.EXPENSE_APPROVE: "Approve or reject project expenses.",
  PermissionKey.PROCUREMENT_READ: "View procurement requests.",
  PermissionKey.PROCUREMENT_CREATE: "Create procurement requests.",
  PermissionKey.PROCUREMENT_MANAGE: "Approve, order, receive or cancel procurement requests.",
  PermissionKey.SITE_LOG_READ: "View site progress logs.",
  PermissionKey.SITE_LOG_CREATE: "Create site progress logs.",
  PermissionKey.SITE_LOG_MANAGE: "Update and delete site progress logs.",
}

##