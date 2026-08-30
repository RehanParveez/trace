export const DRAWINGS_BOQ_PERMISSIONS = {
  DRAWING_READ: "drawing:read",
  DRAWING_CREATE: "drawing:create",
  DRAWING_DELETE: "drawing:delete",
  BOQ_UPDATE: "boq:update",
  BOQ_APPROVE: "boq:approve",
  MATERIAL_LIBRARY_MANAGE: "material_library:manage",
} as const;

export type DrawingsBoqPermission =
  (typeof DRAWINGS_BOQ_PERMISSIONS)[keyof typeof DRAWINGS_BOQ_PERMISSIONS];

export function hasDrawingsBoqPermission(
  permissions: string[] | undefined,
  permission: DrawingsBoqPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}