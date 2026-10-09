export const PERM = {
  DRAWING_READ: "drawing:read",
  DRAWING_CREATE: "drawing:create",
  DRAWING_DELETE: "drawing:delete",
  BOQ_UPDATE: "boq:update",
  BOQ_APPROVE: "boq:approve",
  BOQ_ITEM_CREATE: "boq_item_create",
  BOQ_EXPORT: "boq_export",
  CALC_RUN: "calc:run",
  BOQ_ADJUST: "boq:adjust",
  BOQ_ISSUE: "boq:issue",
  REVIEW_RESOLVE: "review:resolve",
  SCHEDULE_IMPORT: "schedule:import",
  SPACE_MANAGE: "space:manage",
  FINISH_MANAGE: "finish:manage",
  RATEBOOK_MANAGE: "ratebook:manage",
  MATERIAL_LIBRARY_MANAGE: "material_library:manage",
  LABOUR_RATE_MANAGE: "labour_rate_manage",
  RULESET_MANAGE: "ruleset:manage",
  RULESET_PUBLISH: "ruleset:publish",
} as const;

export function hasPerm(permissions: string[], key: string): boolean {
  return permissions.includes(key);
}