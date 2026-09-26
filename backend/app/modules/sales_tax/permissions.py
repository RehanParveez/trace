from app.modules.identity.enums import PermissionKey

SALES_TAX_PERMISSIONS = {
  PermissionKey.SALES_TAX_READ: "View sales tax rates and the tax charge register.",
  PermissionKey.SALES_TAX_MANAGE: "Configure provincial sales tax on services rates for the organization.",
}