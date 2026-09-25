import type { ChangeOrderStatus, ChangeOrderType } from "../types/change-order.types";

export function formatChangeOrderType(type: ChangeOrderType): string {
  switch (type) {
    case "ADDITION": return "Addition";
    case "OMISSION": return "Omission";
    case "VARIATION": return "Variation";
    default: return type;
  }
}

export function formatChangeOrderStatus(status: ChangeOrderStatus): string {
  switch (status) {
    case "DRAFT": return "Draft";
    case "APPROVED": return "Approved";
    case "REJECTED": return "Rejected";
    case "CANCELLED": return "Cancelled";
    default: return status;
  }
}

export function getChangeOrderStatusTone(status: ChangeOrderStatus): "green" | "gold" | "red" | "slate" {
  switch (status) {
    case "APPROVED": return "green";
    case "DRAFT": return "gold";
    case "REJECTED": case "CANCELLED": return "red";
    default: return "slate";
  }
}

export function formatChangeOrderMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  const sign = numeric < 0 ? "-" : "+";
  return `${sign} ${new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(Math.abs(numeric))}`;
}