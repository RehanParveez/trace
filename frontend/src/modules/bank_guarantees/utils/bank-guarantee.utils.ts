import type { BankGuaranteeStatus } from "../types/bank-guarantee.types";

export function formatGuaranteeStatus(status: BankGuaranteeStatus): string {
  switch (status) {
    case "ACTIVE": return "Active";
    case "RENEWED": return "Renewed";
    case "RELEASED": return "Released";
    case "CALLED": return "Called";
    default: return status;
  }
}

export function getGuaranteeStatusTone(status: BankGuaranteeStatus, isExpired: boolean, isExpiringSoon: boolean): "green" | "gold" | "red" | "slate" {
  if (status !== "ACTIVE") return status === "RELEASED" ? "slate" : "red";
  if (isExpired) return "red";
  if (isExpiringSoon) return "gold";
  return "green";
}

export function formatGuaranteeMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(numeric);
}

export function formatGuaranteeDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}