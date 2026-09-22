from app.modules.identity.enums import PermissionKey

MATERIAL_STOCK_PERMISSIONS = {
  PermissionKey.MATERIAL_STOCK_READ: "View material stock reconciliation and issue records.",
  PermissionKey.MATERIAL_STOCK_MANAGE: "Record material issued to work or lost to wastage on site.",
}