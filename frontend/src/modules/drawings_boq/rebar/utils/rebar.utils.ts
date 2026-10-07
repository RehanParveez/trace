import type { RebarRole, RebarScheduleRow, RebarShape } from "../../types/drawings-boq.types";

export const REBAR_ROLES: RebarRole[] = ["COLUMN", "BEAM", "LINTEL", "SLAB", "FOOTING", "PILE", "WALL", "STAIR"];
export const SHAPE_PARAMS = ["A", "B", "C", "D", "E"] as const;
export const REBAR_FILE_EXTENSIONS = [".csv", ".txt", ".xlsx"];
export const REBAR_FILE_MAX_BYTES = 5 * 1024 * 1024;

const FAMILY_PREFIXES = ["COLUMN", "BEAM", "LINTEL", "EDGE_BEAM", "GIRDER", "GROUND_BEAM", "DIAPHRAGM", "SLAB", "RAFT",
  "FOOTING", "FOUNDATION", "PILE", "WALL", "STAIR", "RAMP"];

export const hasRoleFamily = (role: string | null | undefined): boolean =>
  !!role && FAMILY_PREFIXES.some((p) => role.toUpperCase().startsWith(p));

export const num = (v: unknown): number | null => (v === null || v === undefined || v === "" ? null : Number(v));

export function rebarRowBlocker(row: RebarScheduleRow, shapes: RebarShape[]): string | null {
  if (!row.mark) return "Give the bar mark.";
  if (!row.dia_mm || Number(row.dia_mm) <= 0) return "The bar size is missing or not recognised.";
  if (!row.count || row.count <= 0) return "Give the number of bars.";
  const shape = row.shape_code ? shapes.find((s) => s.code === row.shape_code?.toUpperCase()) : undefined;
  if (row.cut_len_mm === null || Number(row.cut_len_mm) <= 0) {
    if (!shape) return "Give the cut length, or a known shape with its dimensions.";
    const missing = shape.segments.filter((p) => !(p in (row.shape_params ?? {})));
    if (missing.length > 0) return `Shape ${shape.code} needs ${[...new Set(missing)].join(", ")}.`;
  }
  if (!row.matched_element_id && !hasRoleFamily(row.role))
    return "Set the member type (column, beam, slab, footing ...) so the steel estimate is switched off.";
  return null;
}

export const shapeDims = (params: Record<string, unknown> | null | undefined): string =>
  Object.entries(params ?? {}).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${Number(v)}`).join(", ");
