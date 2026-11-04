import type { AuditRun, BbsVersionDiff, Finding, FindingClass, FindingRef } from "../types/bbsAudit.types";

export const BBS_FILE_MAX_BYTES = 25 * 1024 * 1024;
export const CLASS_ORDER: FindingClass[] = ["ERROR", "CONFLICT", "METHOD", "CHECK", "MISSING", "EXTRA", "UNVERIFIABLE", "ROUNDING", "NAMING", "INFO"];
export const REASON_MAX = 2000;

export type Tone = "red" | "gold" | "blue" | "green";

export function classTone(c: string): Tone {
  if (c === "ERROR" || c === "CONFLICT") return "red";
  if (c === "METHOD" || c === "MISSING" || c === "EXTRA") return "gold";
  return "blue";
}

export function statusTone(s: string): Tone {
  if (s === "ACCEPTED" || s === "SIGNED") return "green";
  if (s === "REJECTED") return "red";
  return "gold";
}

export function sortedClassCounts(counts: Record<string, number> | undefined): Array<[string, number]> {
  const entries = Object.entries(counts ?? {}).filter(([, n]) => n > 0);
  const rank = (c: string) => { const i = CLASS_ORDER.indexOf(c as FindingClass); return i < 0 ? CLASS_ORDER.length : i; };
  return entries.sort((a, b) => rank(a[0]) - rank(b[0]));
}

export function whereLabel(ref: FindingRef | null | undefined): string {
  if (!ref) return "—";
  const parts: string[] = [];
  if (ref.sheet_name) parts.push(ref.sheet_name);
  if (ref.page) parts.push(`p.${ref.page}`);
  if (ref.member) parts.push(ref.member);
  if (ref.sr) parts.push(`Sr ${ref.sr}`);
  return parts.length > 0 ? parts.join(" · ") : "—";
}

export function kgLabel(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${n > 0 ? "+" : ""}${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function canDecide(f: Finding): boolean {
  return f.status !== "SIGNED";
}

export function reasonProblem(reason: string): string | null {
  const t = reason.trim();
  if (!t) return "required";
  if (t.length > REASON_MAX) return "too long";
  return null;
}

export function readDiff(run: AuditRun | null | undefined): BbsVersionDiff | null {
  const d = run?.diff;
  if (!d || !d.counts) return null;
  return {
    from_version: d.from_version, to_version: d.to_version, counts: d.counts,
    added: d.added ?? [], removed: d.removed ?? [], changed: d.changed ?? [],
  };
}

export function fieldChange(change: [string | null, string | null]): string {
  return `${change[0] ?? "—"} → ${change[1] ?? "—"}`;
}
