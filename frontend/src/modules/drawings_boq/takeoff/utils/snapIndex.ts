import type { Pt, SnapKind, VectorSegment } from "../types/takeoff.types";

export interface SnapHit { x: number; y: number; kind: SnapKind; distance: number; segment: number }

const ALL: SnapKind[] = ["ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE"];

function segDist(px: number, py: number, x1: number, y1: number, x2: number, y2: number): [number, number, number] {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const l2 = dx * dx + dy * dy;
  if (l2 === 0) return [Math.hypot(px - x1, py - y1), x1, y1];
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / l2));
  const cx = x1 + t * dx;
  const cy = y1 + t * dy;
  return [Math.hypot(px - cx, py - cy), cx, cy];
}

function intersect(a: number[], b: number[]): Pt | null {
  const [x1, y1, x2, y2] = a;
  const [x3, y3, x4, y4] = b;
  const den = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3);
  if (Math.abs(den) < 1e-12) return null;
  const t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / den;
  const u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / den;
  const eps = 1e-9;
  if (t < -eps || t > 1 + eps || u < -eps || u > 1 + eps) return null;
  return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)];
}

export class SnapIndex {
  private readonly segs: VectorSegment[];
  private readonly cell: number;
  private readonly cells = new Map<string, number[]>();
  readonly count: number;

  constructor(segments: VectorSegment[], bbox: number[] | null) {
    this.segs = segments;
    this.count = segments.length;
    const w = bbox ? Math.max(bbox[2] - bbox[0], 1) : 1000;
    const h = bbox ? Math.max(bbox[3] - bbox[1], 1) : 1000;
    this.cell = Math.max(8, Math.sqrt((w * h) / Math.max(segments.length, 1)) * 2);
    for (let i = 0; i < segments.length; i++) this.insert(i);
  }

  private key(cx: number, cy: number): string {
    return `${cx},${cy}`;
  }

  private insert(i: number): void {
    const [x1, y1, x2, y2] = this.segs[i];
    const c0x = Math.floor(Math.min(x1, x2) / this.cell);
    const c1x = Math.floor(Math.max(x1, x2) / this.cell);
    const c0y = Math.floor(Math.min(y1, y2) / this.cell);
    const c1y = Math.floor(Math.max(y1, y2) / this.cell);
    if ((c1x - c0x + 1) * (c1y - c0y + 1) > 400) {
     
      const steps = Math.ceil(Math.hypot(x2 - x1, y2 - y1) / (this.cell / 2));
      const seen = new Set<string>();
      for (let s = 0; s <= steps; s++) {
        const t = steps === 0 ? 0 : s / steps;
        const k = this.key(Math.floor((x1 + (x2 - x1) * t) / this.cell), Math.floor((y1 + (y2 - y1) * t) / this.cell));
        if (!seen.has(k)) {
          seen.add(k);
          (this.cells.get(k) ?? this.cells.set(k, []).get(k)!).push(i);
        }
      }
      return;
    }
    for (let cx = c0x; cx <= c1x; cx++) {
      for (let cy = c0y; cy <= c1y; cy++) {
        const k = this.key(cx, cy);
        (this.cells.get(k) ?? this.cells.set(k, []).get(k)!).push(i);
      }
    }
  }

  private candidates(x0: number, y0: number, x1: number, y1: number): number[] {
    const out = new Set<number>();
    for (let cx = Math.floor(x0 / this.cell); cx <= Math.floor(x1 / this.cell); cx++) {
      for (let cy = Math.floor(y0 / this.cell); cy <= Math.floor(y1 / this.cell); cy++) {
        const list = this.cells.get(this.key(cx, cy));
        if (list) for (const i of list) out.add(i);
      }
    }
    return [...out];
  }

  onGeometry(x: number, y: number, tol: number): boolean {
    for (const i of this.candidates(x - tol, y - tol, x + tol, y + tol)) {
      const s = this.segs[i];
      if (segDist(x, y, s[0], s[1], s[2], s[3])[0] <= tol) return true;
    }
    return false;
  }

  nearest(x: number, y: number, radius: number, want: SnapKind[] = ALL): SnapHit | null {
    const wanted = want.length ? want : ALL;
    const near: Array<{ d: number; i: number; cx: number; cy: number }> = [];
    for (const i of this.candidates(x - radius, y - radius, x + radius, y + radius)) {
      const s = this.segs[i];
      const [d, cx, cy] = segDist(x, y, s[0], s[1], s[2], s[3]);
      if (d <= radius) near.push({ d, i, cx, cy });
    }
    if (near.length === 0) return null;
    near.sort((a, b) => a.d - b.d);
    if (wanted.includes("ENDPOINT")) {
      let best: SnapHit | null = null;
      for (const { i } of near) {
        const s = this.segs[i];
        for (const [ex, ey] of [[s[0], s[1]], [s[2], s[3]]] as Array<[number, number]>) {
          const de = Math.hypot(x - ex, y - ey);
          if (de <= radius && (!best || de < best.distance)) best = { x: ex, y: ey, kind: "ENDPOINT", distance: de, segment: i };
        }
      }
      if (best) return best;
    }
    if (wanted.includes("INTERSECTION") && near.length >= 2) {
      let best: SnapHit | null = null;
      const pool = near.slice(0, 14);
      for (let a = 0; a < pool.length; a++) {
        for (let b = a + 1; b < pool.length; b++) {
          const p = intersect(this.segs[pool[a].i], this.segs[pool[b].i]);
          if (p) {
            const de = Math.hypot(x - p[0], y - p[1]);
            if (de <= radius && (!best || de < best.distance)) best = { x: p[0], y: p[1], kind: "INTERSECTION", distance: de, segment: pool[a].i };
          }
        }
      }
      if (best) return best;
    }
    if (wanted.includes("MIDPOINT")) {
      let best: SnapHit | null = null;
      for (const { i } of near) {
        const s = this.segs[i];
        if (Math.hypot(s[2] - s[0], s[3] - s[1]) < 2 || s[4]) continue;
        const mx = (s[0] + s[2]) / 2;
        const my = (s[1] + s[3]) / 2;
        const de = Math.hypot(x - mx, y - my);
        if (de <= radius && (!best || de < best.distance)) best = { x: mx, y: my, kind: "MIDPOINT", distance: de, segment: i };
      }
      if (best) return best;
    }
    if (wanted.includes("EDGE")) {
      const n = near[0];
      return { x: n.cx, y: n.cy, kind: "EDGE", distance: n.d, segment: n.i };
    }
    return null;
  }
}
