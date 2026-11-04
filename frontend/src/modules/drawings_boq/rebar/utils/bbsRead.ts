import type { BbsRead, BbsSheetRead } from "../types/bbsRead.types";

const asNumber = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const asString = (v: unknown): string | null => (typeof v === "string" ? v : null);

function parseSheet(raw: unknown): BbsSheetRead | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const name = asString(r.name);
  const computed = asString(r.computed_kg);
  const rows = asNumber(r.rows);
  if (name === null || computed === null || rows === null) return null;
  return {
    name, rows, computed_kg: computed,
    first_page: asNumber(r.first_page) ?? 0, last_page: asNumber(r.last_page) ?? 0,
    printed_total_kg: asString(r.printed_total_kg), diff_kg: asString(r.diff_kg), reconciled: r.reconciled === true,
  };
}

export function parseBbsRead(meta: Record<string, unknown> | null | undefined): BbsRead | null {
  if (!meta || meta.extraction !== "pk_bbs_feet") return null;
  const rowCount = asNumber(meta.row_count);
  const sheetCount = asNumber(meta.sheet_count);
  if (rowCount === null || sheetCount === null || !Array.isArray(meta.sheets)) return null;
  const sheets = meta.sheets.map(parseSheet).filter((s): s is BbsSheetRead => s !== null);
  return {
    profile: asString(meta.profile) ?? "PK_BBS_FEET",
    pages: asNumber(meta.pages) ?? 0,
    row_count: rowCount,
    sheet_count: sheetCount,
    printed_total_kg: asString(meta.printed_total_kg) ?? "0",
    rows_total_kg: asString(meta.rows_total_kg) ?? "0",
    all_reconciled: meta.all_reconciled === true,
    sheets,
    dropped_repeats: Array.isArray(meta.dropped_repeats) ? (meta.dropped_repeats as BbsRead["dropped_repeats"]) : [],
    unread_count: asNumber(meta.unread_count) ?? 0,
    unread_lines: Array.isArray(meta.unread_lines) ? (meta.unread_lines as BbsRead["unread_lines"]) : [],
  };
}

export const unreconciledSheets = (read: BbsRead): BbsSheetRead[] => read.sheets.filter((s) => !s.reconciled);

export function formatKg(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatDiffKg(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}`;
}

export const pageRange = (s: BbsSheetRead): string => (s.first_page === s.last_page ? `${s.first_page}` : `${s.first_page}–${s.last_page}`);
