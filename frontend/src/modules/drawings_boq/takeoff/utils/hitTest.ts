import type { AreaGeometry, CountGeometry, LengthGeometry, Pt, TakeoffMeasurement } from "../types/takeoff.types";
import { dist, distToPolyline, pointInPolygon, polygonArea } from "./geometry";

export function hitTest(pt: Pt, tolPt: number, measurements: TakeoffMeasurement[]): string | null {
  let best: { id: string; score: number } | null = null;
  const offer = (id: string, score: number) => {
    if (!best || score < best.score) best = { id, score };
  };
  for (const m of measurements) {
    if (m.kind === "LENGTH") {
      const g = m.geometry as LengthGeometry;
      const d = distToPolyline(pt, g.points, Boolean(g.closed));
      if (d <= tolPt) offer(m.id, d);
    } else if (m.kind === "COUNT") {
      const g = m.geometry as CountGeometry;
      for (const p of g.points) {
        const d = dist(pt, p);
        if (d <= tolPt * 1.5) offer(m.id, d);
      }
    } else {
      const g = m.geometry as AreaGeometry;
      const edge = distToPolyline(pt, g.outer, true);
      if (edge <= tolPt) offer(m.id, edge);
      else if (pointInPolygon(pt, g.outer) && !(g.holes ?? []).some((h) => pointInPolygon(pt, h))) offer(m.id, 1e6 + polygonArea(g.outer));
    }
  }
  return best ? (best as { id: string }).id : null;
}
