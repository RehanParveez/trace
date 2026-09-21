export function formatLabourMoney(value: number | string, currency = "PKR"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(numeric);
}

export function formatLabourDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export const SUGGESTED_TRADES = [
  "Mason", "Helper", "Shuttering Carpenter", "Steel Fixer", "Electrician",
  "Plumber", "Painter", "Tile Fixer", "Welder", "Supervisor",
];