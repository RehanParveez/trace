import type { BOQItemStatus, BOQItemType, BOQVersionStatus, DrawingStatus } from "../types/drawings-boq.types";

export function formatDrawingStatus(status: DrawingStatus): string {
  switch (status) {
    case "UPLOADED": return "Uploaded";
    case "PROCESSING": return "Processing";
    case "PARSED": return "Parsed";
    case "FAILED": return "Failed";
    default: return status;
  }
}

export function getDrawingStatusTone(status: DrawingStatus): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "PARSED": return "green";
    case "PROCESSING": return "gold";
    case "UPLOADED": return "blue";
    case "FAILED": return "red";
    default: return "slate";
  }
}

export function isDrawingInProgress(status: DrawingStatus): boolean {
  return status === "UPLOADED" || status === "PROCESSING";
}

export function formatBOQItemStatus(status: BOQItemStatus): string {
  return status === "APPROVED" ? "Approved" : "Draft";
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

export function formatQuantity(value: number | string): string {
  const num = Number(value);
  return Number.isNaN(num) ? "—" : num.toLocaleString("en-PK", { maximumFractionDigits: 2 });
}

export function formatCurrency(value: number | string | null): string {
  if (value === null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 2 }).format(num);
}

export function computeLineTotal(quantity: number | string, unitRate: number | string | null): number | null {
  if (unitRate === null) return null;
  const q = Number(quantity);
  const r = Number(unitRate);
  return Number.isNaN(q) || Number.isNaN(r) ? null : q * r;
}

export function formatBOQItemType(type: BOQItemType): string {
  switch (type) {
    case "MATERIAL": return "Material";
    case "LABOUR": return "Labour";
    case "CUSTOM": return "Additional";
    default: return type;
  }
}

export function formatBOQVersionStatus(status: BOQVersionStatus): string {
  return status === "ACTIVE" ? "Active" : "Superseded";
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}