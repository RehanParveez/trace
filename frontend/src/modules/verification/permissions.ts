export const VERIFICATION_PERMISSIONS = {
  PROGRESS_CLAIM_READ: "progress_claim:read",
  PROGRESS_CLAIM_CREATE: "progress_claim:create",
  PROGRESS_CLAIM_UPDATE: "progress_claim:update",
  PROGRESS_CLAIM_SUBMIT: "progress_claim:submit",
  PROGRESS_CLAIM_REVIEW: "progress_claim:review",
  PHOTO_BOQ_LINK_READ: "photo_boq_link:read",
  PHOTO_BOQ_LINK_MANAGE: "photo_boq_link:manage",
} as const;

export type VerificationPermission =
  (typeof VERIFICATION_PERMISSIONS)[keyof typeof VERIFICATION_PERMISSIONS];

export function hasVerificationPermission(
  permissions: string[] | undefined,
  permission: VerificationPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}