import type { ExpectInput, ExpectRun, InputState } from "../types/bbsExpect.types";

export const STATE_ORDER: InputState[] = ["PRINTED", "DERIVED", "DEFAULTED", "MISSING"];
export const HEIGHT_FLOORS = ["BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "ROOF", "MUMTY"] as const;
export const STOCK_ASSUMED_FT = 40;

export function stateTone(state: string): "green" | "blue" | "gold" | "red" {
  if (state === "PRINTED") return "green";
  if (state === "DERIVED") return "blue";
  if (state === "DEFAULTED") return "gold";
  return "red";
}

export function shareRows(run: ExpectRun | null | undefined): Array<{ state: InputState; count: number; percent: string }> {
  const s = run?.stats.shares;
  return STATE_ORDER.map((state) => ({ state, count: s?.counts[state] ?? 0, percent: s && s.total > 0 ? `${((s.shares[state] ?? 0) * 100).toFixed(1)}%` : "—" }));
}

export function kgText(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
}

export function flagText(flag: string | null): string {
  if (!flag) return "";
  return flag.split(",").map((f) => f.replace(/_/g, " ").toLowerCase()).join(", ");
}

export function inputValueText(i: Pick<ExpectInput, "value">): string {
  const v = i.value;
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.map((x) => (Array.isArray(x) ? x.join(" ") : String(x))).join("; ");
  return String(v);
}

export function numberOrNull(text: string): number | null | "bad" {
  const t = text.trim();
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : "bad";
}

export function heightsPayload(values: Record<string, string>): Record<string, number> | "bad" {
  const out: Record<string, number> = {};
  for (const [floor, text] of Object.entries(values)) {
    const n = numberOrNull(text);
    if (n === "bad") return "bad";
    if (n !== null) out[floor] = n;
  }
  return out;
}

export function parseMemberInputs(text: string): { ok: true; value: Record<string, Record<string, unknown>> } | { ok: false; error: string } {
  const t = text.trim();
  if (t === "") return { ok: true, value: {} };
  try {
    const v: unknown = JSON.parse(t);
    if (v === null || typeof v !== "object" || Array.isArray(v)) return { ok: false, error: "object" };
    for (const fields of Object.values(v as Record<string, unknown>)) {
      if (fields === null || typeof fields !== "object" || Array.isArray(fields)) return { ok: false, error: "fields" };
    }
    return { ok: true, value: v as Record<string, Record<string, unknown>> };
  } catch {
    return { ok: false, error: "json" };
  }
}

export function completeLabel(run: ExpectRun | null | undefined): string {
  return run ? `${run.complete_count} / ${run.member_count}` : "—";
}
