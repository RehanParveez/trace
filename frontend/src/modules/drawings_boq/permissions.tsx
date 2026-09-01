export const DRAWINGS_BOQ_PERMISSIONS = {
  DRAWING_READ: "drawing:read",
  DRAWING_CREATE: "drawing:create",
  DRAWING_DELETE: "drawing:delete",
  BOQ_UPDATE: "boq:update",
  BOQ_APPROVE: "boq:approve",
  BOQ_ITEM_CREATE: "boq_item:create",
  BOQ_EXPORT: "boq:export",
  MATERIAL_LIBRARY_MANAGE: "material_library:manage",
  LABOUR_RATE_MANAGE: "labour_rate:manage",
} as const;

export type DrawingsBoqPermission =
  (typeof DRAWINGS_BOQ_PERMISSIONS)[keyof typeof DRAWINGS_BOQ_PERMISSIONS];

export function hasDrawingsBoqPermission(
  permissions: string[] | undefined,
  permission: DrawingsBoqPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}