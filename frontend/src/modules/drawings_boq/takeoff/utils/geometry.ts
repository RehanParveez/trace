import type { Pt } from "../types/takeoff.types";
import { round4 } from "./viewport";

export function dist(a: Pt | number[], b: Pt | number[]): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

export function polylineLength(points: Pt[], closed = false): number {
  let total = 0;
  for (let i = 1; i < points.length; i++) total += dist(points[i - 1], points[i]);
  if (closed && points.length > 2) total += dist(points[points.length - 1], points[0]);
  return total;
}

export function polygonArea(ring: Pt[]): number {
  let s = 0;
  for (let i = 0; i < ring.length; i++) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[(i + 1) % ring.length];
    s += x1 * y2 - x2 * y1;
  }
  return Math.abs(s) / 2;
}

export function pointInPolygon(p: Pt, ring: Pt[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export function distToSegment(p: Pt | number[], a: Pt | number[], b: Pt | number[]): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return dist(p, a);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

export function distToPolyline(p: Pt, points: Pt[], closed = false): number {
  let best = Infinity;
  const n = points.length;
  for (let i = 1; i < n; i++) best = Math.min(best, distToSegment(p, points[i - 1], points[i]));
  if (closed && n > 2) best = Math.min(best, distToSegment(p, points[n - 1], points[0]));
  if (n === 1) best = dist(p, points[0]);
  return best;
}

function orient(a: Pt, b: Pt, c: Pt): number {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}

function properCross(a: Pt, b: Pt, c: Pt, d: Pt): boolean {
  const o1 = orient(a, b, c);
  const o2 = orient(a, b, d);
  const o3 = orient(c, d, a);
  const o4 = orient(c, d, b);
  return ((o1 > 0 && o2 < 0) || (o1 < 0 && o2 > 0)) && ((o3 > 0 && o4 < 0) || (o3 < 0 && o4 > 0));
}

/** True when a closed ring crosses itself (cheap O(n^2) check, only for drawing-time feedback; the server decides). */
export function ringSelfIntersects(ring: Pt[]): boolean {
  const n = ring.length;
  if (n < 4) return false;
  for (let i = 0; i < n; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % n];
    for (let j = i + 1; j < n; j++) {
      if (j === i || (j + 1) % n === i || (i + 1) % n === j) continue;
      if (properCross(a, b, ring[j], ring[(j + 1) % n])) return true;
    }
  }
  return false;
}

export function orthoConstrain(from: Pt, p: Pt): Pt {
  return Math.abs(p[0] - from[0]) >= Math.abs(p[1] - from[1]) ? [p[0], from[1]] : [from[0], p[1]];
}

export function trimSegment(line: [Pt, Pt], trimStartPt: number, trimEndPt: number): [Pt, Pt] {
  const [a, b] = line;
  const len = dist(a, b);
  if (len === 0) return [a, b];
  const ux = (b[0] - a[0]) / len;
  const uy = (b[1] - a[1]) / len;
  const s = Math.min(Math.max(trimStartPt, 0), len / 2);
  const e = Math.min(Math.max(trimEndPt, 0), len / 2);
  return [
    [round4(a[0] + ux * s), round4(a[1] + uy * s)],
    [round4(b[0] - ux * e), round4(b[1] - uy * e)],
  ];
}

export function bboxOf(points: Pt[]): { x0: number; y0: number; x1: number; y1: number } | null {
  if (points.length === 0) return null;
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const [x, y] of points) {
    x0 = Math.min(x0, x);
    y0 = Math.min(y0, y);
    x1 = Math.max(x1, x);
    y1 = Math.max(y1, y);
  }
  return { x0, y0, x1, y1 };
}

export function roundPt(p: Pt | number[]): Pt {
  return [round4(p[0]), round4(p[1])];
}

export function dedupeConsecutive(points: Pt[], tol = 1e-6): Pt[] {
  const out: Pt[] = [];
  for (const p of points) {
    if (out.length === 0 || dist(out[out.length - 1], p) > tol) out.push(p);
  }
  return out;
}
