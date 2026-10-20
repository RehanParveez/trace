import type { AreaWorksStats, DerivedStats } from "../types/drawings-boq.types";

export interface OpeningAreaView {
  ran: boolean;
  reason: string | null;
  doors: number;
  windows: number;
  doorAreaM2: string;
  windowAreaM2: string;
  noSize: number;
  skipped: string[];
}

export interface RoofTreatmentView {
  ran: boolean;
  reason: string | null;
  roofSlabs: number;
  areaM2: string;
  noPlan: number;
}

export function openingAreaView(stats: DerivedStats | null | undefined): OpeningAreaView | null {
  const s: AreaWorksStats | undefined = stats?.opening_area;
  if (!s || !s.enabled) return null;
  return {
    ran: Boolean(s.ran),
    reason: s.reason ?? null,
    doors: Number(s.doors ?? 0),
    windows: Number(s.windows ?? 0),
    doorAreaM2: String(s.door_area_m2 ?? "0"),
    windowAreaM2: String(s.window_area_m2 ?? "0"),
    noSize: Number(s.no_size ?? 0),
    skipped: Object.keys(s.skipped ?? {}),
  };
}

export function roofTreatmentView(stats: DerivedStats | null | undefined): RoofTreatmentView | null {
  const s: AreaWorksStats | undefined = stats?.roof_treatment;
  if (!s || !s.enabled) return null;
  return { ran: Boolean(s.ran), reason: s.reason ?? null, roofSlabs: Number(s.roof_slabs ?? 0), areaM2: String(s.area_m2 ?? "0"), noPlan: Number(s.no_plan ?? 0) };
}

export function areaReasonWords(reason: string | null | undefined): string {
  switch (reason) {
    case "SWITCHED_OFF":
      return "The setting is off.";
    case "NO_OPENINGS":
      return "The model has no door or window with a size.";
    case "ALL_ITEMS_ALREADY_MEASURED":
      return "Both items were already measured from the model or a drawing.";
    case "ALREADY_MEASURED":
      return "The roof treatment was already measured from the model or a drawing.";
    case "NO_ROOF_SLAB":
      return "The model has no roof slab that it measured. A slab is a roof only when the model says so.";
    case "NOTHING_TO_MEASURE":
      return "The roof slabs gave no area.";
    default:
      return reason ?? "";
  }
}
