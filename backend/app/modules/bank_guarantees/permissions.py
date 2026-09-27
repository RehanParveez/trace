from app.modules.identity.enums import PermissionKey

BANK_GUARANTEE_PERMISSIONS = {
  PermissionKey.BANK_GUARANTEE_READ: "View bank guarantees and their expiry status.",
  PermissionKey.BANK_GUARANTEE_MANAGE: "Record and renew bank guarantees.",
  PermissionKey.BANK_GUARANTEE_RELEASE: "Release or mark bank guarantees as called.",
}