import type { Num } from "../../types/drawings-boq.types";
import type {AnalysisComponentSource, AnalysisComponentType, DiffStatus, RateAttempt, RateBook, RateBookStatus, RateEscalation, RateItemInput,
} from "../types/pricing.types";

type Tone = "green" | "red" | "blue" | "gold" | "slate";

export const RATE_BOOK_STATUSES: readonly RateBookStatus[] = ["DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"];

export const RATE_BOOK_STATUS_LABEL: Record<RateBookStatus, string> = {
  DRAFT: "Draft",
  ACTIVE: "Active",
  SUPERSEDED: "Superseded",
  ARCHIVED: "Archived",
};

export function rateBookStatusTone(status: RateBookStatus): Tone {
  switch (status) {
    case "ACTIVE":
      return "green";
    case "DRAFT":
      return "gold";
    case "SUPERSEDED":
      return "blue";
    default:
      return "slate";
  }
}

export const RATE_SOURCE_LABEL: Record<string, string> = {
  PROJECT_OVERRIDE: "Project override",
  RATE_BOOK: "Rate book",
  LIBRARY: "Material library",
  AI_SUGGESTED: "AI suggested",
  MANUAL: "Manual",
};

export function rateSourceLabel(source: string | null | undefined): string {
  if (!source) return "Unpriced";
  return RATE_SOURCE_LABEL[source] ?? source;
}

export function rateSourceTone(source: string | null | undefined): Tone {
  switch (source) {
    case "RATE_BOOK":
      return "green";
    case "PROJECT_OVERRIDE":
      return "blue";
    case "AI_SUGGESTED":
      return "gold";
    case "LIBRARY":
    case "MANUAL":
      return "slate";
    default:
      return "red";
  }
}

export const COMPONENT_TYPES: readonly AnalysisComponentType[] = ["MATERIAL", "LABOUR", "PLANT", "OTHER"];
export const COMPONENT_TYPE_LABEL: Record<AnalysisComponentType, string> = {
  MATERIAL: "Material",
  LABOUR: "Labour",
  PLANT: "Plant",
  OTHER: "Other",
};

export const COMPONENT_SOURCES: readonly AnalysisComponentSource[] = [
  "DIRECT", "RATE_ITEM", "LABOUR_RATE", "MATERIAL_LIBRARY",
];
export const COMPONENT_SOURCE_LABEL: Record<AnalysisComponentSource, string> = {
  DIRECT: "Typed rate",
  RATE_ITEM: "Rate in this book",
  LABOUR_RATE: "Labour rate",
  MATERIAL_LIBRARY: "Material library",
};

export function diffStatusTone(status: DiffStatus): Tone {
  switch (status) {
    case "ADDED":
      return "green";
    case "REMOVED":
      return "red";
    case "CHANGED":
      return "gold";
    default:
      return "slate";
  }
}

export const DIFF_STATUS_LABEL: Record<DiffStatus, string> = {
  ADDED: "Added",
  REMOVED: "Removed",
  CHANGED: "Changed",
  UNCHANGED: "Unchanged",
};

type Translate = (key: string, defaultValue: string, options?: Record<string, unknown>) => string;

export function attemptLabel(attempt: RateAttempt, t: Translate): string {
  const where =
    attempt.source === "RATE_BOOK"
      ? t("pricing.explain.whereBook", "Rate book {{code}}", { code: attempt.book ?? "" }).trim()
      : attempt.source === "PROJECT_OVERRIDE"
        ? t("pricing.explain.whereOverride", "Project override")
        : t("pricing.explain.whereLibrary", "Material library");
  switch (attempt.result) {
    case "used":
      return t("pricing.explain.attemptUsed", "{{where}}: used", { where });
    case "unit_mismatch":
      return attempt.units?.length
        ? t("pricing.explain.attemptMismatchHas", "{{where}}: unit does not match (has {{units}})", { where, units: attempt.units.join(", ") })
        : t("pricing.explain.attemptMismatch", "{{where}}: unit does not match", { where });
    default:
      return t("pricing.explain.attemptNone", "{{where}}: no rate for this work item", { where });
  }
}

export function toNumber(value: Num | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

export function formatFactor(value: Num | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `×${n.toFixed(4)}`;
}

export function factorToPercent(value: Num | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const pct = (n - 1) * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

export function formatPercent(value: Num | null | undefined, digits = 1): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `${n.toFixed(digits)}%`;
}

export function formatSigned(value: Num | null | undefined, digits = 2): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const text = Math.abs(n).toLocaleString("en-PK", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  if (n === 0) return text;
  return `${n > 0 ? "+" : "−"}${text}`;
}

export function deltaClass(value: Num | null | undefined): string {
  const n = toNumber(value);
  if (n === null || n === 0) return "text-[var(--color-text-secondary)]";
  return n > 0 ? "text-[var(--color-danger)]" : "text-[var(--color-success)]";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function todayIso(): string {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}

export function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function parsePositive(value: string): number | null {
  const n = Number(value.replace(/,/g, ""));
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function parseNonNegative(value: string): number | null {
  if (value.trim() === "") return null;
  const n = Number(value.replace(/,/g, ""));
  return Number.isFinite(n) && n >= 0 ? n : null;
}

export function rateBookTitle(book: Pick<RateBook, "code" | "immutable_version" | "edition">): string {
  return `${book.code} v${book.immutable_version}${book.edition ? ` · ${book.edition}` : ""}`;
}

export function isBookEditable(book: RateBook): boolean {
  return !book.is_system && book.status === "DRAFT";
}

export function canEscalate(book: RateBook): boolean {
  return !book.is_system && (book.status === "DRAFT" || book.status === "ACTIVE");
}

export function canPriceWith(book: RateBook): boolean {
  return book.status === "ACTIVE" || book.status === "SUPERSEDED";
}

export function effectiveEscalation(
  escalations: RateEscalation[],
  trade: string | null | undefined,
  asOf: string,
): RateEscalation | null {
  const wanted = (trade ?? "").trim().toLowerCase();
  let best: { rank: [number, string]; row: RateEscalation } | null = null;
  for (const row of escalations) {
    if (row.effective_from > asOf) continue;
    const scope = (row.trade_scope || "ALL").trim().toLowerCase();
    if (scope !== "all" && scope !== wanted) continue;
    const rank: [number, string] = [scope === "all" ? 0 : 1, row.effective_from];
    if (!best || rank[0] > best.rank[0] || (rank[0] === best.rank[0] && rank[1] > best.rank[1])) {
      best = { rank, row };
    }
  }
  return best ? best.row : null;
}

export const RATE_IMPORT_MAX_BYTES = 5 * 1024 * 1024;
export const RATE_BULK_MAX_ROWS = 2000;
export const RATE_CSV_TEMPLATE =
  "work_item_code,unit,rate,trade,csr_ref,description\r\nRCC-M20,m3,18500,Concrete,CSR-4.1,Reinforced concrete M20\r\n";

export interface ParsedRateRows {
  rows: RateItemInput[];
  errors: string[];
}

function splitLine(line: string, delimiter: string): string[] {
  if (delimiter === "\t") return line.split("\t").map((c) => c.trim());
  const cells: string[] = [];
  let current = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  cells.push(current.trim());
  return cells;
}

export function parseRateRows(text: string): ParsedRateRows {
  const rows: RateItemInput[] = [];
  const errors: string[] = [];
  const lines = text.split(/\r?\n/).filter((line) => line.trim() !== "");
  lines.forEach((line, index) => {
    const delimiter = line.includes("\t") ? "\t" : ",";
    const cells = splitLine(line, delimiter);
    const rateText = (cells[2] ?? "").replace(/,/g, "");
    if (index === 0 && rateText !== "" && Number.isNaN(Number(rateText))) return;
    const code = (cells[0] ?? "").trim();
    const unit = (cells[1] ?? "").trim();
    const rate = Number(rateText);
    if (!code || !unit || rateText === "" || !Number.isFinite(rate) || rate < 0) {
      errors.push(`Line ${index + 1}: needs a work item code, a unit and a rate of zero or more.`);
      return;
    }
    rows.push({
      work_item_code: code,
      unit,
      rate,
      trade: cells[3] || null,
      csr_ref: cells[4] || null,
      description: cells[5] || null,
    });
  });
  if (rows.length > RATE_BULK_MAX_ROWS) {
    errors.push(`At most ${RATE_BULK_MAX_ROWS} rows can be pasted at once. Upload a CSV for larger lists.`);
  }
  return { rows, errors };
}

export function previewAnalysisRate(
  lines: Array<{ coefficient: number; unit_rate: number | null }>,
  basisQuantity: number,
  overheadPct: number,
  profitPct: number,
): number | null {
  if (basisQuantity <= 0) return null;
  if (lines.some((l) => l.unit_rate === null)) return null;
  const round2 = (v: number) => Math.round((v + Number.EPSILON) * 100) / 100;
  const cost = lines.reduce((sum, l) => sum + round2(l.coefficient * (l.unit_rate as number)), 0);
  const overhead = round2((cost * overheadPct) / 100);
  const profit = round2(((cost + overhead) * profitPct) / 100);
  return round2((cost + overhead + profit) / basisQuantity);
}

export const RATE_BOOKS_PATH = "/app/drawings_boq/rate-books";
export const rateBookPath = (id: string) => `${RATE_BOOKS_PATH}/${id}`;

export type OverrideState = "active" | "scheduled" | "expired" | "revoked";

export function overrideState(
  override: { revoked_at: string | null; effective_from: string | null; effective_to: string | null },
  today: string = todayIso(),
): OverrideState {
  if (override.revoked_at) return "revoked";
  if (override.effective_to && override.effective_to < today) return "expired";
  if (override.effective_from && override.effective_from > today) return "scheduled";
  return "active";
}

export const OVERRIDE_STATE_LABEL: Record<OverrideState, string> = {
  active: "Active",
  scheduled: "Scheduled",
  expired: "Expired",
  revoked: "Revoked",
};

export function overrideStateTone(state: OverrideState): Tone {
  switch (state) {
    case "active":
      return "green";
    case "scheduled":
      return "blue";
    case "expired":
      return "slate";
    default:
      return "red";
  }
}