from app.modules.identity.enums import PermissionKey

VERIFICATION_PERMISSIONS = {
  PermissionKey.PROGRESS_CLAIM_READ: (
    "View project progress claims and verification evidence."
  ),
  PermissionKey.PROGRESS_CLAIM_CREATE: (
    "Create project progress claims."
  ),
  PermissionKey.PROGRESS_CLAIM_UPDATE: (
    "Update draft progress claims."
  ),
  PermissionKey.PROGRESS_CLAIM_SUBMIT: (
    "Submit progress claims for verification."
  ),
  PermissionKey.PROGRESS_CLAIM_REVIEW: (
    "Review and approve or reject progress claims."
  ),
  PermissionKey.PHOTO_BOQ_LINK_READ: (
    "View photo to BOQ verification links."
  ),
  PermissionKey.PHOTO_BOQ_LINK_MANAGE: (
    "Create and remove photo to BOQ verification links."
  ),
}