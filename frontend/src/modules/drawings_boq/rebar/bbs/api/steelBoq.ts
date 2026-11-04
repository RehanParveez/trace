import type { SteelBoq, SteelBoqState } from "../types/steelBoq.types";

function n(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const v = Number(value);
  return Number.isFinite(v) ? v : null;
}

export function qty(value: string | null | undefined): string {
  const v = n(value);
  return v === null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}

export function signedQty(value: string | null | undefined): string {
  const v = n(value);
  if (v === null) return "—";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${qty(String(Math.abs(v)))}`;
}

export const STATE_WORDS: Record<SteelBoqState, string> = {
  ADDED: "The audit is not on the bill yet.",
  REPLACED: "The bill carries an older audit; it is out of date.",
  UNCHANGED: "The bill carries the audited steel.",
  CLEARED: "The bill carries an audit that the project's steel line no longer uses.",
  NOTHING: "The audit changes nothing on the bill.",
};

export function actionWords(d: SteelBoq): string | null {
  if (d.state === "ADDED" || d.state === "REPLACED") return "Put the audited steel on the bill";
  if (d.state === "CLEARED") return "Remove the audit from the bill";
  return null;
}

export function canPress(d: SteelBoq, canAdjust: boolean): boolean {
  return canAdjust && actionWords(d) !== null;
}

export function itemSentence(d: SteelBoq): string {
  const now = `${qty(d.quantity_now)} ${d.unit}`;
  const after = `${qty(d.quantity_after)} ${d.unit}`;
  if (d.state === "UNCHANGED") return `${d.item_name} stands at ${now}, with the audit's ${signedQty(d.delta)} ${d.unit} on it.`;
  if (d.state === "NOTHING") return `${d.item_name} stands at ${now}.`;
  return `${d.item_name} stands at ${now} and would stand at ${after} (${signedQty(d.delta)} ${d.unit}).`;
}

export function whyNothing(d: SteelBoq): string | null {
  if (d.state !== "NOTHING") return null;
  if (d.source !== "BBS_AUDITED") return "The project's steel line is not the audited figure.";
  return d.applied_count === 0 ? "No finding is accepted yet." : "The accepted findings add up to no kg.";
}
