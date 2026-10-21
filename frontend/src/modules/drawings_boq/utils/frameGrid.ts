import type { DrawingElement } from "../types/drawings-boq.types";

export interface FrameInfo {
  xM: number | null;
  yM: number | null;
  label: string;
}

export interface FrameGrid {
  xs: number[]; 
  ys: number[]; 
  originXmm: number;
  originYmm: number;
  tolMm: number;
}

export const DEFAULT_TOL_MM = 300;
const POINT_TYPES = new Set(["IfcColumn", "IfcFooting", "IfcPile"]);
const LINEAR_TYPES = new Set(["IfcBeam", "IfcWall", "IfcWallStandardCase", "IfcMember"]);

function num(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

interface Box { x0: number; y0: number; x1: number; y1: number }

export function boxOf(e: Pick<DrawingElement, "bbox_min_x_mm" | "bbox_min_y_mm" | "bbox_max_x_mm" | "bbox_max_y_mm">): Box | null {
  const x0 = num(e.bbox_min_x_mm), y0 = num(e.bbox_min_y_mm), x1 = num(e.bbox_max_x_mm), y1 = num(e.bbox_max_y_mm);
  if (x0 === null || y0 === null || x1 === null || y1 === null) return null;
  return { x0: Math.min(x0, x1), y0: Math.min(y0, y1), x1: Math.max(x0, x1), y1: Math.max(y0, y1) };
}

export function clusterLines(values: number[], tolMm: number): number[] {
  const sorted = [...values].filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  const lines: { sum: number; n: number }[] = [];
  for (const v of sorted) {
    const last = lines[lines.length - 1];
    if (last && Math.abs(v - last.sum / last.n) <= tolMm) {
      last.sum += v;
      last.n += 1;
    } else {
      lines.push({ sum: v, n: 1 });
    }
  }
  return lines.map((l) => l.sum / l.n);
}

export function letterOf(n: number): string {
  let s = "";
  let k = n;
  do {
    s = String.fromCharCode(65 + (k % 26)) + s;
    k = Math.floor(k / 26) - 1;
  } while (k >= 0);
  return s;
}

function nearest(lines: number[], v: number, tolMm: number): number {
  let best = -1;
  let gap = Infinity;
  lines.forEach((l, i) => {
    const d = Math.abs(l - v);
    if (d < gap) {
      gap = d;
      best = i;
    }
  });
  return best >= 0 && gap <= tolMm ? best : -1;
}

export function buildGrid(elements: DrawingElement[], tolMm: number = DEFAULT_TOL_MM): FrameGrid | null {
  const boxes = elements.map((e) => ({ e, b: boxOf(e) })).filter((r): r is { e: DrawingElement; b: Box } => r.b !== null);
  if (boxes.length === 0) return null;
  const points = boxes.filter((r) => POINT_TYPES.has(r.e.ifc_type));
  const lines = points.length >= 2;
  return {
    xs: lines ? clusterLines(points.map((r) => (r.b.x0 + r.b.x1) / 2), tolMm) : [],
    ys: lines ? clusterLines(points.map((r) => (r.b.y0 + r.b.y1) / 2), tolMm) : [],
    tolMm,
    originXmm: Math.min(...boxes.map((r) => r.b.x0)),
    originYmm: Math.min(...boxes.map((r) => r.b.y0)),
  };
}

const round2 = (n: number) => Math.round(n * 100) / 100;

export const END_REACH_MM = 250;

function pointLabel(grid: FrameGrid, x: number, y: number, reachX: number, reachY: number): string {
  const i = nearest(grid.xs, x, reachX);
  const j = nearest(grid.ys, y, reachY);
  return i >= 0 && j >= 0 ? `${letterOf(j)}-${i + 1}` : "";
}

export function frameOf(e: DrawingElement, grid: FrameGrid | null): FrameInfo {
  const b = boxOf(e);
  if (!b || !grid) return { xM: null, yM: null, label: "" };
  const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
  const info = { xM: round2((cx - grid.originXmm) / 1000), yM: round2((cy - grid.originYmm) / 1000) };
  if (LINEAR_TYPES.has(e.ifc_type)) {
    const alongX = b.x1 - b.x0 >= b.y1 - b.y0;
    const tol = grid.tolMm, wide = tol + END_REACH_MM;
    const first = alongX ? pointLabel(grid, b.x0, cy, wide, tol) : pointLabel(grid, cx, b.y0, tol, wide);
    const last = alongX ? pointLabel(grid, b.x1, cy, wide, tol) : pointLabel(grid, cx, b.y1, tol, wide);
    return { ...info, label: first && last && first !== last ? `${first} to ${last}` : first || last };
  }
  return { ...info, label: pointLabel(grid, cx, cy, grid.tolMm, grid.tolMm) };
}

export function withFrames<T extends DrawingElement>(elements: T[], tolMm: number = DEFAULT_TOL_MM): (T & { frame: FrameInfo })[] {
  const grid = buildGrid(elements, tolMm);
  return elements.map((e) => ({ ...e, frame: frameOf(e, grid) }));
}

export function frameText(e: { frame?: FrameInfo | null }): string {
  return e.frame?.label ?? "";
}

export function coordText(e: { frame?: FrameInfo | null }): string {
  const f = e.frame;
  return f && f.xM !== null && f.yM !== null ? `${f.xM.toFixed(2)}, ${f.yM.toFixed(2)}` : "";
}