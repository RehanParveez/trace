import type { Num } from "../../../types/drawings-boq.types";
import type { CheckStatus, ImportStatus, ImportRow, RateGap } from "../types/schedules.types";

type Tone = "green" | "red" | "blue" | "gold" | "slate";

export const RATE_IMPORTS_PATH = "/app/drawings_boq/rate-imports";
export const rateImportPath = (id: string) => `${RATE_IMPORTS_PATH}/${id}`;

export const IMPORT_MAX_BYTES = 50 * 1024 * 1024;

export const IMPORT_STATUS_LABEL: Record<ImportStatus, string> = {
  UPLOADED: "Waiting to be read",
  PARSING: "Reading the file…",
  REVIEW: "Ready to review",
  PUBLISHED: "Loaded into a rate book",
  FAILED: "Could not be read",
  CANCELLED: "Cancelled",
};

export function importStatusTone(status: ImportStatus): Tone {
  switch (status) {
    case "REVIEW":
      return "gold";
    case "PUBLISHED":
      return "green";
    case "FAILED":
      return "red";
    case "UPLOADED":
    case "PARSING":
      return "blue";
    default:
      return "slate";
  }
}

export function checkTone(status: CheckStatus): Tone {
  return status === "pass" ? "green" : status === "warn" ? "gold" : "red";
}

export const CHECK_STATUS_LABEL: Record<CheckStatus, string> = { pass: "OK", warn: "Check", fail: "Problem" };

export const LAYOUT_PROFILES: Array<{ value: string; label: string; hint: string }> = [
  { value: "GENERIC", label: "Standard (one rate column)", hint: "Item no, description, unit, rate." },
  { value: "GENERIC_TWO_RATES_METRIC", label: "Two rate columns (per-unit and metric)", hint: "Reads both and checks they agree." },
];

export const FLAG_LABEL: Record<string, string> = {
  NO_ITEM_NO: "No item number",
  UNIT_UNKNOWN: "Unit not recognised",
  UNIT_AMBIGUOUS: "Unit ambiguous",
  RATE_MISSING: "No rate",
  RATE_ZERO: "Rate is zero",
  RATE_OUTLIER: "Rate looks off",
  DUPLICATE_ITEM_NO: "Duplicate item no",
  SECOND_PASS_MISSING: "Rate not found on re-read",
  ALT_RATE_MISMATCH: "Two rates disagree",
  WRAPPED_DESCRIPTION: "Description joined",
  BASIS_APPLIED: "Per-block rate divided",
};

export const FLAG_HELP: Record<string, string> = {
  NO_ITEM_NO: "The row has no item number in the document.",
  UNIT_UNKNOWN: "The pricing engine can't convert this unit. Pick the unit before mapping.",
  UNIT_AMBIGUOUS: "The unit is ambiguous (for example 'ton'). Pick the unit before mapping.",
  RATE_MISSING: "No rate could be read.",
  RATE_ZERO: "The rate reads as zero.",
  RATE_OUTLIER: "The rate is far from the others with the same unit in this chapter. Check it against the page.",
  DUPLICATE_ITEM_NO: "The same item number appears more than once with a different rate.",
  SECOND_PASS_MISSING: "The rate was not found when the page was read a second way. Check it against the page.",
  ALT_RATE_MISMATCH: "The two rate columns disagree once converted to the same unit.",
  WRAPPED_DESCRIPTION: "The description ran over several lines and was joined.",
  BASIS_APPLIED: "The rate is for a block of units (for example per 100 cft) and was divided down to one unit.",
};

export const REVIEW_FLAGS = new Set([
  "NO_ITEM_NO", "UNIT_UNKNOWN", "RATE_MISSING", "RATE_ZERO", "RATE_OUTLIER", "DUPLICATE_ITEM_NO", "SECOND_PASS_MISSING", "ALT_RATE_MISMATCH", "UNIT_AMBIGUOUS",
]);

export function flagTone(flag: string): Tone {
  return REVIEW_FLAGS.has(flag) ? "gold" : "slate";
}

export function formatRate(value: Num | null | undefined, digits = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-PK", { minimumFractionDigits: digits, maximumFractionDigits: Math.max(digits, 4) });
}

export function printedRate(row: Pick<ImportRow, "rate" | "basis_qty" | "unit" | "unit_raw">): string {
  if (row.rate === null || row.rate === undefined) return "—";
  const basis = Number(row.basis_qty);
  const unit = row.unit ?? row.unit_raw ?? "";
  return basis !== 1 && !Number.isNaN(basis) ? `${formatRate(row.rate)} per ${basis} ${unit}` : `${formatRate(row.rate)}${unit ? ` / ${unit}` : ""}`;
}

export function rowStatus(row: ImportRow): "skipped" | "review" | "mapped" | "unmapped" {
  if (row.skipped) return "skipped";
  if (row.needs_review) return "review";
  return row.work_item_code ? "mapped" : "unmapped";
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export const GAP_REASON_LABEL: Record<RateGap["reason"], string> = {
  NO_CODE: "No work item code",
  NO_RATE: "No rate in any book",
  UNIT_MISMATCH: "Rate exists in another unit",
};

export function gapTone(reason: RateGap["reason"]): Tone {
  return reason === "UNIT_MISMATCH" ? "gold" : "red";
}

export function downloadName(code: string, version: number, format: string): string {
  return `${code}_v${version}.${format}`;
}
