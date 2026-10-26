import type { ConfidenceStats, CoverageStats } from "../types/drawings-boq.types";

export type TrustBand = "HIGH" | "MEDIUM" | "LOW";
export const TRUST_BANDS: readonly TrustBand[] = ["HIGH", "MEDIUM", "LOW"];

export type CoverageGapKey = "rejected" | "skipped_by_role" | "unmapped" | "other_unmeasured";
const GAP_KEYS: readonly CoverageGapKey[] = ["rejected", "skipped_by_role", "unmapped", "other_unmeasured"];

export interface CoverageDetailItem {
  name: string;
  count: number;
}

export interface CoverageView {
  total: number;
  measured: number;
  percent: number;
  gaps: { key: CoverageGapKey; count: number }[];
  detail: { rejected: CoverageDetailItem[]; skipped_by_role: CoverageDetailItem[]; unmapped: CoverageDetailItem[] };
}

export const REJECTED_REASON: Record<string, string> = {
  INVALID_ELEMENT: "Failed validation when the model was read",
  NON_CONCRETE_MATERIAL: "The material is not concrete, but the role is measured as concrete",
  NO_QUANTITY: "No usable quantity in the model's own quantities or its geometry",
  MISSING_DIMENSION: "A dimension the role needs is missing",
  READ_ERROR: "The element could not be read",
  STEEL_NO_QUANTITY: "Steel element with no volume or length",
  IFC_BAR_NO_DIAMETER: "The bar gives no diameter",
  IFC_BAR_NO_LENGTH: "The bar gives no length",
};

function detailItems(record: Record<string, number> | undefined): CoverageDetailItem[] {
  return Object.entries(record ?? {})
    .map(([name, n]) => ({ name, count: count(n) }))
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function count(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
}

export function coverageView(stats: CoverageStats | null | undefined): CoverageView | null {
  if (!stats) {
    return null;
  }
  const total = count(stats.elements);
  if (total === 0) {
    return null;
  }
  const measured = Math.min(count(stats.measured), total);
  const percent = measured === total ? 100 : Math.min(99, Math.floor((measured / total) * 100));
  const gaps = GAP_KEYS.map((key) => ({ key, count: count(stats[key]) })).filter((gap) => gap.count > 0);
  return {
    total, measured, percent, gaps,
    detail: {
      rejected: detailItems(stats.rejected_codes),
      skipped_by_role: detailItems(stats.skipped_roles),
      unmapped: detailItems(stats.unmapped_types),
    },
  };
}

export interface ConfidenceBandView {
  band: TrustBand;
  rows: number;
  volumeM3: number;
  volumeShare: number | null;
}

export interface ConfidenceSourceView {
  key: string;
  rows: number;
  volumeM3: number;
  share: number | null;
}

export interface ConfidenceView {
  rows: number;
  totalVolumeM3: number;
  bands: ConfidenceBandView[];
  sources: ConfidenceSourceView[];
}

function volume(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

export function confidenceView(stats: ConfidenceStats | null | undefined): ConfidenceView | null {
  if (!stats || count(stats.rows) === 0) {
    return null;
  }
  const totalVolumeM3 = TRUST_BANDS.reduce((sum, band) => sum + volume(stats.volume_m3?.[band]), 0);
  const bands = TRUST_BANDS.map((band) => {
    const volumeM3 = volume(stats.volume_m3?.[band]);
    return {
      band,
      rows: count(stats.bands?.[band]),
      volumeM3,
      volumeShare: totalVolumeM3 > 0 ? volumeM3 / totalVolumeM3 : null,
    };
  });
  const sources = Object.entries(stats.by_geometry ?? {})
    .map(([key, entry]) => {
      const volumeM3 = volume(entry?.m3);
      return { key, rows: count(entry?.rows), volumeM3, share: totalVolumeM3 > 0 ? volumeM3 / totalVolumeM3 : null };
    })
    .sort((a, b) => b.volumeM3 - a.volumeM3 || (a.key < b.key ? -1 : 1));
  return { rows: count(stats.rows), totalVolumeM3, bands, sources };
}

export interface GeometryBasis {
  kind: string;
  check: string | null;
  factor: number | null;
  key: string;
}

export function geometryBasis(trace: unknown): GeometryBasis | null {
  const inputs = trace && typeof trace === "object" ? (trace as { inputs?: unknown }).inputs : null;
  if (!inputs || typeof inputs !== "object") {
    return null;
  }
  const i = inputs as Record<string, unknown>;
  if (typeof i.geometry_kind !== "string" || i.geometry_kind === "") {
    return null;
  }
  const check = typeof i.volume_check === "string" && i.volume_check !== "" ? i.volume_check : null;
  const factor = i.confidence_factor === undefined || i.confidence_factor === null ? Number.NaN : Number(i.confidence_factor);
  return {
    kind: i.geometry_kind,
    check,
    factor: Number.isFinite(factor) ? factor : null,
    key: check ? `${i.geometry_kind}:${check}` : i.geometry_kind,
  };
}

type Translate = (key: string, fallback: string) => string;

const SOURCE_LABELS: Record<string, string> = {
  EXTRUDED_PROFILE: "Exact profile and length from the model",
  AXIS_SWEPT: "Profile swept along its axis",
  "EXTRUDED_PROFILE:PRISM_MESH": "Profile and 3D mesh agree, model volume differs",
  "EXTRUDED_PROFILE:MESH_QTO": "Cut profile, 3D mesh and model volume agree",
  "EXTRUDED_PROFILE:PRISM_QTO": "Profile and model volume agree, 3D mesh differs",
  "EXTRUDED_PROFILE:MESH_ALONE": "Profile, 3D mesh and model volume differ, 3D mesh billed",
  "AXIS_SWEPT:PRISM_MESH": "Profile and 3D mesh agree, model volume differs",
  "AXIS_SWEPT:MESH_QTO": "Cut profile, 3D mesh and model volume agree",
  "AXIS_SWEPT:PRISM_QTO": "Profile and model volume agree, 3D mesh differs",
  "AXIS_SWEPT:MESH_ALONE": "Profile, 3D mesh and model volume differ, 3D mesh billed",
  "BOX_ONLY:VERIFIED": "Bounding box, volume agrees with the 3D mesh",
  "BOX_ONLY:MESH": "Bounding box, volume from the 3D mesh",
  "BOX_ONLY:MISMATCH": "Bounding box, model and 3D mesh volumes disagree",
  BOX_ONLY: "Bounding box, volume not cross-checked",
  QTO_ONLY: "Model quantity only, no geometry",
};

export function geometrySourceLabel(key: string, t: Translate): string {
  const fallback = SOURCE_LABELS[key] ?? key.replace(/[_:]/g, " ").toLowerCase();
  return t(`boq.trust.source.${key.replace(/:/g, "_")}`, fallback);
}

export function bandTone(band: TrustBand): "green" | "gold" | "red" {
  return band === "HIGH" ? "green" : band === "MEDIUM" ? "gold" : "red";
}
