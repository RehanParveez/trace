export function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function fmtDecimal(value: string | number | null | undefined, dp = 3): string {
  const n = num(value);
  if (n === null) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: dp, useGrouping: false });
}

export function fmtPct(value: string | number | null | undefined, dp = 0): string {
  const n = num(value);
  return n === null ? "—" : `${(n * 100).toFixed(dp)}%`;
}

export function fmtPlain(value: string | number | null | undefined, dp = 2): string {
  const n = num(value);
  return n === null ? "—" : n.toFixed(dp);
}

export function fmtMm(mm: number | null | undefined): string {
  if (mm === null || mm === undefined || !Number.isFinite(mm)) return "—";
  const abs = Math.abs(mm);
  if (abs >= 1000) return `${(mm / 1000).toFixed(3)} m`;
  return `${mm.toFixed(1)} mm`;
}

export function fmtRatio(ratio: string | number | null | undefined): string {
  const n = num(ratio);
  if (n === null) return "—";
  return `1:${Number.isInteger(n) ? n : n.toFixed(2).replace(/\.?0+$/, "")}`;
}
