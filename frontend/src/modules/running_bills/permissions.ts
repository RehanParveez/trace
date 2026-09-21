export const RUNNING_BILL_PERMISSIONS = {
  RUNNING_BILL_READ: "running_bill:read",
  RUNNING_BILL_CREATE: "running_bill:create",
  RUNNING_BILL_ISSUE: "running_bill:issue",
} as const;

export type RunningBillPermission =
  (typeof RUNNING_BILL_PERMISSIONS)[keyof typeof RUNNING_BILL_PERMISSIONS];