import type { CrossCheck, CrossChecks } from "../types/takeoff.types";

export function toLookAt(data: CrossChecks | undefined): CrossCheck[] {
  return (data?.checks ?? []).filter((c) => c.status !== "PASS");
}

export function passed(data: CrossChecks | undefined): CrossCheck[] {
  return (data?.checks ?? []).filter((c) => c.status === "PASS");
}

export function pagesLine(pages: number[]): string {
  const p = [...new Set(pages)].sort((a, b) => a - b);
  if (!p.length) return "";
  if (p.length === 1) return `Page ${p[0]}`;
  return `Pages ${p.slice(0, -1).join(", ")} and ${p[p.length - 1]}`;
}

export function summaryLine(data: CrossChecks | undefined): string {
  if (!data || !data.checks.length) return "";
  const bits: string[] = [];
  if (data.warnings) bits.push(data.warnings === 1 ? "1 disagrees" : `${data.warnings} disagree`);
  if (data.info) bits.push(data.info === 1 ? "1 half read" : `${data.info} half read`);
  if (data.passed) bits.push(data.passed === 1 ? "1 agrees" : `${data.passed} agree`);
  return bits.join(" · ");
}

export function checkTone(status: CrossCheck["status"]): "red" | "gold" | "green" {
  return status === "WARN" ? "red" : status === "INFO" ? "gold" : "green";
}
