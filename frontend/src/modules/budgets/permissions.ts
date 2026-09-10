export const BUDGET_PERMISSIONS = {
  BUDGET_READ: "budget:read",
  BUDGET_MANAGE: "budget:manage",
} as const;

export type BudgetPermission = (typeof BUDGET_PERMISSIONS)[keyof typeof BUDGET_PERMISSIONS];

export function hasBudgetPermission(
  permissions: string[] | undefined,
  permission: BudgetPermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}