import type { Draft } from "../store/takeoffView.store";
import type { AreaGeometry, CountGeometry, Geometry, LengthGeometry, Pt, TakeoffMeasurement } from "../types/takeoff.types";
import { dedupeConsecutive, ringSelfIntersects, roundPt } from "./geometry";

export interface DraftGeometry { geometry: Geometry | null; hint: string | null }

export function draftGeometry(d: Draft): DraftGeometry {
  if (d.kind === "LENGTH") {
    const points = dedupeConsecutive(d.points.map(roundPt));
    if (points.length < 2) return { geometry: null, hint: "Click at least two points." };
    const g: LengthGeometry = { points, closed: d.closed };
    return { geometry: g, hint: null };
  }
  if (d.kind === "COUNT") {
    const points = d.points.map(roundPt);
    if (points.length < 1) return { geometry: null, hint: "Click to place the first point." };
    const g: CountGeometry = { points };
    return { geometry: g, hint: null };
  }
  const outer = dedupeConsecutive(d.points.map(roundPt));
  if (outer.length < 3) return { geometry: null, hint: "Click at least three corners." };
  if (ringSelfIntersects(outer)) return { geometry: null, hint: "The outline crosses itself. Remove the last point (Backspace) and redraw." };
  const holes: Pt[][] = [];
  for (let i = 0; i < d.holes.length; i++) {
    const ring = dedupeConsecutive(d.holes[i].map(roundPt));
    if (ring.length < 3) {
      if (d.activeHole === i) return { geometry: null, hint: "Finish the hole: it needs at least three corners." };
      continue;
    }
    if (ringSelfIntersects(ring)) return { geometry: null, hint: "A hole crosses itself. Redraw it." };
    holes.push(ring);
  }
  const g: AreaGeometry = { outer, holes };
  return { geometry: g, hint: null };
}

export function geometryPoints(m: Pick<TakeoffMeasurement, "kind" | "geometry">): Pt[] {
  if (m.kind === "AREA") return (m.geometry as AreaGeometry).outer;
  return (m.geometry as LengthGeometry | CountGeometry).points;
}
