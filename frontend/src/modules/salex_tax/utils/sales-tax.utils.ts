import type { SalesTaxAuthority } from "../types/sales-tax.types";

export function formatSalesTaxAuthority(authority: SalesTaxAuthority): string {
  switch (authority) {
    case "PRA": return "Punjab (PRA)";
    case "SRB": return "Sindh (SRB)";
    case "KPRA": return "Khyber Pakhtunkhwa (KPRA)";
    case "BRA": return "Balochistan (BRA)";
    case "ICT": return "Islamabad Capital Territory (ICT)";
    default: return authority;
  }
}

export function formatSalesTaxMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(numeric);
}