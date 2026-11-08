import { formatCurrency } from "../../../utils/drawings-boq.utils";
import type { ExportKind, FlowLine, LineState, ProfileSource, StepKey, StepState } from "../types/flow.types";

export const STEP_ORDER: StepKey[] = ["upload", "read", "quantities", "review", "boq", "export"];

export const STEP_TEXT: Record<StepKey, string> = {
  upload: "Upload the drawings",
  read: "Read the drawings",
  quantities: "Work out the quantities",
  review: "Review what the reader left open",
  boq: "Priced BOQ",
  export: "Export",
};

export const STATE_TONE: Record<StepState, "green" | "gold" | "blue" | "slate"> = {
  DONE: "green",
  OPEN: "slate",
  RUNNING: "blue",
  FAILED: "gold",
  READY: "blue",
};

export const STATE_TEXT: Record<StepState, string> = {
  DONE: "Done",
  OPEN: "Not yet",
  RUNNING: "Running",
  FAILED: "Needs attention",
  READY: "Ready",
};

export const LINE_TONE: Record<LineState, "green" | "gold" | "blue"> = {
  MEASURED: "green",
  ASSUMED: "gold",
  PART_ASSUMED: "blue",
};

export const SOURCE_TEXT: Record<ProfileSource, string> = {
  REQUEST: "chosen for this sitting",
  COMPANY: "your company's profile",
  DEFAULT: "the software's default: your company has set none",
};

export const SEGMENT_TEXT: Record<string, string> = {
  waiting_to_start: "Upload to the start of the reading",
  reading: "Reading the drawings",
  reaching_review: "Reading done to the review opened",
  review_to_boq: "Review opened to the BOQ opened",
  boq_to_export: "BOQ opened to the first export",
  sitting: "Upload to the first export",
};

export const EXPORT_TEXT: Record<ExportKind, string> = {
  xlsx: "Workbook (xlsx)",
  priced_pdf: "Priced BOQ (PDF)",
  client_pdf: "Client report (PDF)",
};

export const EXPORTS: ExportKind[] = ["xlsx", "priced_pdf", "client_pdf"];

export function moneyOrDash(value: number | null): string {
  return value === null ? "-" : formatCurrency(value);
}

export function secondsText(value: number | null): string {
  if (value === null) return "not recorded";
  if (value < 90) return `${value.toFixed(1)} s`;
  const minutes = Math.floor(value / 60);
  return `${minutes} min ${Math.round(value - minutes * 60)} s`;
}

export function rangeText(line: FlowLine): string {
  if (line.low_pct === null || line.high_pct === null) return "-";
  const sign = (v: number) => (v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1));
  return `${sign(line.low_pct)}% / ${sign(line.high_pct)}%`;
}

export function saveBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
