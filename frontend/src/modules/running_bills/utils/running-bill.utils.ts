import type { RunningBillStatus } from "../types/running-bill.types";

export function formatRunningBillStatus(status: RunningBillStatus): string {
  switch (status) {
    case "DRAFT":
      return "Draft";
    case "ISSUED":
      return "Issued";
    case "CANCELLED":
      return "Cancelled";
    default:
      return status;
  }
}

export function getRunningBillStatusTone(
  status: RunningBillStatus,
): "green" | "gold" | "red" | "slate" {
  switch (status) {
    case "ISSUED":
      return "green";
    case "DRAFT":
      return "gold";
    case "CANCELLED":
      return "red";
    default:
      return "slate";
  }
}

export function formatBillMoney(
  value: number | string,
  currency: string,
): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(numeric);
}

export function formatBillDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function openBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.setTimeout(() => window.URL.revokeObjectURL(url), 30_000);
}