import type { ExpenseStatus } from "../types/expense.types";

export function formatExpenseStatus(status: ExpenseStatus): string {
  switch (status) {
    case "PENDING": return "Pending";
    case "APPROVED": return "Approved";
    case "REJECTED": return "Rejected";
    default: return status;
  }
}

export function getExpenseStatusTone(status: ExpenseStatus): "green" | "gold" | "red" | "slate" {
  switch (status) {
    case "APPROVED": return "green";
    case "PENDING": return "gold";
    case "REJECTED": return "red";
    default: return "slate";
  }
}

export function formatExpenseAmount(value: number | string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(numeric);
}

export function formatExpenseDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}