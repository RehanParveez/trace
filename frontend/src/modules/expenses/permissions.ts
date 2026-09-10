export const EXPENSE_PERMISSIONS = {
  EXPENSE_READ: "expense:read",
  EXPENSE_CREATE: "expense:create",
  EXPENSE_APPROVE: "expense:approve",
} as const;

export type ExpensePermission = (typeof EXPENSE_PERMISSIONS)[keyof typeof EXPENSE_PERMISSIONS];

export function hasExpensePermission(
  permissions: string[] | undefined,
  permission: ExpensePermission,
): boolean {
  return permissions?.includes(permission) ?? false;
}