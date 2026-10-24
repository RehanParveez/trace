import type { TakeoffCandidate } from "../../types/takeoff.types";

export const CROP_PX = 420;

export function cropKey(c: Pick<TakeoffCandidate, "id" | "geometry">): string {
  const text = JSON.stringify(c.geometry ?? {});
  let h = 5381;
  for (let i = 0; i < text.length; i += 1) h = ((h * 33) ^ text.charCodeAt(i)) >>> 0;
  return `${c.id}:${h.toString(36)}`;
}

export function hasPosition(c: Pick<TakeoffCandidate, "geometry">): boolean {
  const g = (c.geometry ?? {}) as { points?: unknown[]; outer?: unknown[] };
  return (g.outer?.length ?? 0) > 0 || (g.points?.length ?? 0) > 0;
}

export function cropAlt(label: string, pageNo: number): string {
  return `${label} (sheet ${pageNo})`;
}
