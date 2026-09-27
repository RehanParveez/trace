export function formatCashFlowMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  const sign = numeric < 0 ? "-" : "";
  return `${sign}${new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(Math.abs(numeric))}`;
}
export function formatCashFlowDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short" }).format(date);
}
export function formatCashFlowCategory(category: string): string {
  switch (category) {
    case "PROCUREMENT": return "Procurement";
    case "LABOUR": return "Labour";
    case "SUBCONTRACTOR": return "Subcontractor";
    case "CLIENT_COLLECTION": return "Client collection";
    default: return category;
  }
}