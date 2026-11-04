import type { AuditRun, DrawingRef, Finding, FindingConvention } from "../types/bbsAudit.types";

const BASIS: Record<string, string> = {
  EXPECTATION: "Weight effect: the drawing's figures replace the schedule's",
  ESTIMATE: "Weight effect is an estimate: it rests on an input that was assumed or derived",
  BBS_ROWS: "Weight shown is what the schedule bills for these rows",
};

export function basisLabel(f: Pick<Finding, "effect_basis">): string {
  return f.effect_basis ? BASIS[f.effect_basis] ?? f.effect_basis : "";
}

export function isEstimate(f: Pick<Finding, "effect_basis">): boolean {
  return f.effect_basis === "ESTIMATE";
}

export function conventionLabel(c: FindingConvention | null | undefined): string {
  if (!c) return "";
  return `If this is the project's convention: ${c.key} = ${String(c.value)}`;
}

export function drawingLabel(r: DrawingRef | null | undefined): string {
  if (!r) return "";
  const parts: string[] = ["Drawing"];
  if (r.sheet_no) parts.push(r.sheet_no);
  if (r.page) parts.push(`p.${r.page}`);
  if (r.what) parts.push(r.what);
  return parts.join(" · ");
}

export function crossLine(totals: AuditRun["totals"] | undefined): string {
  const x = totals?.crosscheck;
  if (!x) return "";
  const share = x.match_stats?.share_without_asking;
  const bits = [`${x.compared_rows ?? 0} rows compared`];
  if (typeof share === "number") bits.push(`${(share * 100).toFixed(1)}% matched without asking`);
  if (x.net_effect_kg !== undefined) bits.push(`net ${x.net_effect_kg} kg (errors ${x.net_effect_kg_error_only ?? "0.00"} kg)`);
  const blocked = Object.keys(x.unchecked_blockers ?? {});
  if (blocked.length > 0) bits.push(`not checked for lack of: ${blocked.join(", ")}`);
  return bits.join(" · ");
}
