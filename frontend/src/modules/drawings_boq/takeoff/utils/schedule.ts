import type { DrawingFacts, FloorCheck, FloorCheckStatus, ScheduleOpening } from "../types/takeoff.types";
import { mmText, mmToFeetInches } from "./facts";
import { hasChecks } from "./check";
import { hasStructure } from "./structure";

export interface OpeningGroup { type: string; rows: ScheduleOpening[]; }

const TYPE_ORDER = ["DOOR", "WINDOW", "VENTILATOR", "OPENING"];

export function sizeText(widthMm: number, heightMm: number): string {
  return `${mmToFeetInches(widthMm)} × ${mmToFeetInches(heightMm)} (${Math.round(widthMm)} × ${Math.round(heightMm)} mm)`;
}

export function inchesText(mm: number): string {
  return (mm / 25.4).toFixed(1).replace(/\.0$/, "");
}

export function lintelText(widthMm: number, depthMm: number): string {
  return `${inchesText(widthMm)}×${inchesText(depthMm)} in`;
}

export function m2Text(v: number, digits = 1): string {
  return `${v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })} m²`;
}

export function metresText(v: number): string {
  return `${v.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} m`;
}

export function groupOpenings(facts: DrawingFacts | undefined): OpeningGroup[] {
  const rows = facts?.schedule?.openings ?? [];
  const by = new Map<string, ScheduleOpening[]>();
  for (const r of rows) {
    const list = by.get(r.type) ?? [];
    list.push(r);
    by.set(r.type, list);
  }
  return [...by.entries()]
    .sort(([a], [b]) => (TYPE_ORDER.indexOf(a) + 1 || 99) - (TYPE_ORDER.indexOf(b) + 1 || 99))
    .map(([type, list]) => ({ type, rows: list }));
}

export const OPENING_TYPE_TITLE: Record<string, string> = { DOOR: "Doors", WINDOW: "Windows", VENTILATOR: "Ventilators", OPENING: "Other openings" };

export const FLOOR_STATUS_TONE: Record<FloorCheckStatus, "ok" | "warn" | "muted"> = { OK: "ok", LOW: "warn", HIGH: "warn", NOT_READ: "muted" };

export function wallHeightBasisText(basis: string | null): string {
  if (basis === "SECTION") return "printed on the building section";
  if (basis === "LEVEL_MARKS") return "level marks less slab";
  if (basis === "TYPICAL") return "typical floor height less slab";
  return "";
}

export function netWallArea(f: FloorCheck): number {
  return f.brick_9_m2 + f.brick_45_m2 + f.rcc_m2;
}

export function floorHasItems(f: FloorCheck): boolean {
  return f.status !== "NOT_READ";
}

export function hasSchedule(facts: DrawingFacts | undefined): boolean {
  return (facts?.schedule?.openings?.length ?? 0) > 0 || (facts?.schedule?.areas?.length ?? 0) > 0 || (facts?.schedule?.lintels?.length ?? 0) > 0 || (facts?.floors?.length ?? 0) > 0 || !!facts?.suggest?.wall_height || hasStructure(facts) || hasChecks(facts);
}

export function suggestedHeightText(facts: DrawingFacts | undefined): string | null {
  const s = facts?.suggest?.wall_height;
  if (!s) return null;
  return `${mmToFeetInches(s.value_mm)} (${mmText(s.value_mm)})`;
}