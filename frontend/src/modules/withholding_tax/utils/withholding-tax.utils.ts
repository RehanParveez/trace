import type { WHTCategory } from "../types/withholding-tax.types";

export function formatWHTCategory(category: WHTCategory): string {
  switch (category) {
    case "GOODS_SUPPLY": return "Supply of goods";
    case "SERVICES": return "Rendering of services";
    case "CONTRACTS_EXECUTION": return "Execution of contracts";
    default: return category;
  }
}

export function formatWHTMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(numeric);
}