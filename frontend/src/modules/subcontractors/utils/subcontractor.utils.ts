import type { SubcontractAgreementStatus, SubcontractorBillStatus } from "../types/subcontractor.types";

export function formatMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(numeric);
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function getAgreementStatusTone(status: SubcontractAgreementStatus): "green" | "gold" | "red" {
  if (status === "ACTIVE") return "green";
  if (status === "COMPLETED") return "gold";
  return "red";
}

export function getBillStatusTone(status: SubcontractorBillStatus): "green" | "gold" | "red" {
  if (status === "ISSUED") return "green";
  if (status === "DRAFT") return "gold";
  return "red";
}

export function openBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename;
  document.body.appendChild(link); link.click(); document.body.removeChild(link);
  window.setTimeout(() => window.URL.revokeObjectURL(url), 30_000);
}