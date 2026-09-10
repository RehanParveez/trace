import type { ProcurementStatus } from "../types/procurement.types";

export function formatProcurementStatus(status: ProcurementStatus): string {
  switch (status) {
    case "REQUESTED": return "Requested";
    case "APPROVED": return "Approved";
    case "ORDERED": return "Ordered";
    case "RECEIVED": return "Received";
    case "CANCELLED": return "Cancelled";
    default: return status;
  }
}

export function getProcurementStatusTone(status: ProcurementStatus): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "RECEIVED": return "green";
    case "APPROVED": case "ORDERED": return "blue";
    case "REQUESTED": return "gold";
    case "CANCELLED": return "red";
    default: return "slate";
  }
}

export function formatProcurementAmount(value: number | string | null): string {
  if (value === null) return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(numeric);
}

export function formatProcurementDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export const PROCUREMENT_NEXT_STATUS: Record<ProcurementStatus, ProcurementStatus | null> = {
  REQUESTED: "APPROVED",
  APPROVED: "ORDERED",
  ORDERED: "RECEIVED",
  RECEIVED: null,
  CANCELLED: null,
};

export function formatNextProcurementActionLabel(status: ProcurementStatus): string | null {
  switch (status) {
    case "REQUESTED": return "Approve";
    case "APPROVED": return "Mark ordered";
    case "ORDERED": return "Mark received";
    default: return null;
  }
}