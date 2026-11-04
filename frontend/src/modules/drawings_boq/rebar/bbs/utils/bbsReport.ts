import type { Finding } from "../types/bbsAudit.types";
import type { CropSide, FindingAction, ReportSummary } from "../types/bbsReport.types";
import { reasonProblem } from "./bbsAudit";

export const SIGN_LIMIT = "Signing a convention changes this project's rules only. A firm-wide convention is a separate rule-book decision.";

function n(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const v = Number(value);
  return Number.isFinite(v) ? v : null;
}

export function kgPlain(value: string | null | undefined): string {
  const v = n(value);
  return v === null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function pctLabel(value: string | null | undefined): string {
  const v = n(value);
  if (v === null) return "—";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %`;
}

export function signedKg(value: string | null | undefined): string {
  const v = n(value);
  if (v === null) return "—";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function availableActions(f: Pick<Finding, "status" | "finding_class" | "convention">): FindingAction[] {
  if (f.status === "SIGNED") return [];
  const out: FindingAction[] = ["ACCEPTED", "REJECTED"];
  if (f.status !== "OPEN") out.push("OPEN");
  if (canSign(f)) out.push("SIGN");
  return out;
}

export function canSign(f: Pick<Finding, "status" | "finding_class" | "convention">): boolean {
  return f.status !== "SIGNED" && f.finding_class === "METHOD" && Boolean(f.convention?.key);
}

export function actionBlocked(reason: string): string | null {
  return reasonProblem(reason);
}

export function signSentence(f: Pick<Finding, "convention">): string {
  const c = f.convention;
  return c ? `Signing sets ${c.key} = ${String(c.value)} for this project. ${SIGN_LIMIT}` : SIGN_LIMIT;
}

export function cropSrc(side: CropSide | null | undefined): string | null {
  return side?.png_base64 ? `data:image/png;base64,${side.png_base64}` : null;
}

export function totalsLine(s: Pick<ReportSummary, "bbs_total_kg" | "expected_total_kg" | "diff_kg" | "diff_pct">): string {
  return `Expected ${kgPlain(s.expected_total_kg)} kg against the schedule's ${kgPlain(s.bbs_total_kg)} kg: ${signedKg(s.diff_kg)} kg (${pctLabel(s.diff_pct)})`;
}

export function basisSentence(effectByBasis: Record<string, string>): string {
  const est = n(effectByBasis.ESTIMATE);
  if (est === null || est === 0) return "";
  return `${signedKg(effectByBasis.ESTIMATE)} kg of this rests on an input that was assumed or derived, not read from the drawing.`;
}

export function exportName(version: number, ext: "xlsx" | "md"): string {
  return `bbs-audit-v${version}.${ext}`;
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function saveBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
