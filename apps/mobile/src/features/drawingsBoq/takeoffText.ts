import type { TakeoffMeasurement, TakeoffReconMode, TakeoffSheet } from "../../api/types";
import { formatNumber } from "./ui";

export type Tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) => string;

export const RECON_MODES: TakeoffReconMode[] = ["AUTO", "ADD", "REPLACE_MODEL", "VERIFY_ONLY"];

export function reconLabel(tx: Tx, mode: string): string {
  switch (mode) {
    case "AUTO":
      return tx("takeoff.recon.AUTO", "Automatic");
    case "ADD":
      return tx("takeoff.recon.ADD", "Add to model");
    case "REPLACE_MODEL":
      return tx("takeoff.recon.REPLACE_MODEL", "Replace model");
    case "VERIFY_ONLY":
      return tx("takeoff.recon.VERIFY_ONLY", "Verify only");
    default:
      return mode;
  }
}

export function reconHint(tx: Tx, mode: string): string {
  switch (mode) {
    case "AUTO":
      return tx("takeoff.reconHint.AUTO", "Counted when the model does not already measure this work item; otherwise it is left out and flagged for review.");
    case "ADD":
      return tx("takeoff.reconHint.ADD", "Always added on top of the model quantity.");
    case "REPLACE_MODEL":
      return tx("takeoff.reconHint.REPLACE_MODEL", "Replaces the model quantity for this work item.");
    case "VERIFY_ONLY":
      return tx("takeoff.reconHint.VERIFY_ONLY", "Not counted. Compared with the model so you can see the difference.");
    default:
      return "";
  }
}

export function sheetTitle(tx: Tx, sheet: Pick<TakeoffSheet, "label" | "page_no">): string {
  const label = sheet.label?.trim();
  return label ? `${tx("takeoff.page", "Page {{n}}", { n: sheet.page_no })} · ${label}` : tx("takeoff.page", "Page {{n}}", { n: sheet.page_no });
}

export function prepTone(status: string): "good" | "warn" | "bad" | "neutral" {
  if (status === "READY") return "good";
  if (status === "FAILED") return "bad";
  return "warn";
}

export function measurementTone(status: string): "good" | "warn" | "neutral" {
  return status === "CONFIRMED" ? "good" : status === "DRAFT" ? "warn" : "neutral";
}

export function measurementTitle(tx: Tx, m: TakeoffMeasurement): string {
  return m.label?.trim() || m.tag?.trim() || m.work_item_code || tx("takeoff.measurement", "Measurement");
}

export function quantityText(m: Pick<TakeoffMeasurement, "computed">): string {
  const c = m.computed;
  if (!c) return "—";
  if (c.error) return c.error.message;
  if (c.quantity === undefined || c.quantity === null) return "—";
  return `${formatNumber(c.quantity)} ${c.unit ?? ""}`.trim();
}

export function toNumber(text: string): number | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

export function ratioText(ratio: string | number | null | undefined): string {
  if (ratio === null || ratio === undefined) return "—";
  const n = Number(ratio);
  return Number.isFinite(n) ? `1:${formatNumber(n, 2)}` : String(ratio);
}

export function warningText(warning: string | { code?: string; message?: string }): string {
  return typeof warning === "string" ? warning : warning.message ?? warning.code ?? "";
}

export function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}