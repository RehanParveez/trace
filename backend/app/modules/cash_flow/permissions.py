from app.modules.identity.enums import PermissionKey

CASH_FLOW_PERMISSIONS = {
  PermissionKey.CASH_FLOW_READ: "View the cash flow forecast.",
  PermissionKey.CASH_FLOW_MANAGE: "Adjust the payment-terms assumptions the forecast is built on.",
}