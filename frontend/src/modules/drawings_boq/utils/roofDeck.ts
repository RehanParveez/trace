import type { DerivedStats, RoofDeckStats } from "../types/drawings-boq.types";

export interface RoofDeckView {
  ran: boolean;
  reason: string | null;
  roofs: number;
  roofAreaM2: string;
  membraneM2: string | null;
  cobaM3: string | null;
  screedM2: string | null;
  cobaThicknessMm: number | null;
  thicknessAssumed: boolean;
  layers: string[];
  skipped: string[];
}

export function roofDeckView(stats: DerivedStats | null | undefined): RoofDeckView | null {
  const s: RoofDeckStats | undefined = stats?.roof_deck;
  if (!s || !s.enabled) return null;
  const layers = Array.isArray(s.layers) ? s.layers.map(String) : [];
  const thickness = s.coba_thickness_mm == null ? null : Number(s.coba_thickness_mm);
  return {
    ran: Boolean(s.ran),
    reason: s.reason ?? null,
    roofs: Number(s.roofs ?? 0),
    roofAreaM2: String(s.roof_area_m2 ?? "0"),
    membraneM2: layers.includes("MEMBRANE") ? String(s.membrane_m2 ?? "0") : null,
    cobaM3: layers.includes("COBA") ? String(s.coba_m3 ?? "0") : null,
    screedM2: layers.includes("SCREED") ? String(s.screed_m2 ?? "0") : null,
    cobaThicknessMm: thickness !== null && Number.isFinite(thickness) ? thickness : null,
    thicknessAssumed: s.coba_thickness_source === "default",
    layers,
    skipped: Object.keys(s.skipped ?? {}),
  };
}

export function roofDeckReasonWords(reason: string | null | undefined): string {
  switch (reason) {
    case "SWITCHED_OFF":
      return "The setting is off.";
    case "NO_ROOF_TREATMENT":
      return "There is no roof treatment area to put the layers on. Measure the roof on the drawing, or switch on the roof treatment from the model's roof slabs.";
    case "NO_LAYER_WANTED":
      return "Every layer is switched off.";
    case "ALL_LAYERS_ALREADY_MEASURED":
      return "Every layer was already measured from the model or a drawing.";
    case "NOTHING_TO_MEASURE":
      return "The roof areas gave no quantity.";
    default:
      return reason ?? "";
  }
}

const LAYER_NAMES: Record<string, string> = { MEMBRANE: "Membrane", COBA: "Coba", SCREED: "Screed" };

export function roofLayerName(layer: string): string {
  return LAYER_NAMES[layer] ?? layer;
}
