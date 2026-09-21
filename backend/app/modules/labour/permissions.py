from app.modules.identity.enums import PermissionKey

LABOUR_PERMISSIONS = {
  PermissionKey.LABOUR_READ: "View labour sources, workers, deployments and attendance.",
  PermissionKey.LABOUR_MANAGE: "Manage labour sources, workers, deployments and record attendance.",
  PermissionKey.LABOUR_PAYMENT_MANAGE: "Record labour advances and wage payments.",
}