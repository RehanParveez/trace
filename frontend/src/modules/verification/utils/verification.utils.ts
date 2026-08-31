import type { ProgressClaimStatus } from "../types/verification.types";

export function formatClaimStatus(status: ProgressClaimStatus): string {
  switch (status) {
    case "DRAFT": return "Draft";
    case "SUBMITTED": return "Submitted";
    case "APPROVED": return "Approved";
    case "REJECTED": return "Rejected";
    default: return status;
  }
}

export function getClaimStatusTone(status: ProgressClaimStatus): "green" | "gold" | "red" | "slate" {
  switch (status) {
    case "APPROVED": return "green";
    case "SUBMITTED": return "gold";
    case "REJECTED": return "red";
    default: return "slate";
  }
}

export function formatClaimDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function formatClaimQuantity(value: number | string, unit: string): string {
  const num = Number(value);
  return Number.isNaN(num) ? "—" : `${num.toLocaleString("en-PK", { maximumFractionDigits: 2 })} ${unit}`;
}

export function formatClaimPercentage(value: number | string): string {
  const num = Number(value);
  return Number.isNaN(num) ? "—" : `${num.toFixed(1)}%`;
}