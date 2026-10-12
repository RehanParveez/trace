import type { Pt } from "../types/takeoff.types";

export type Matrix = [number, number, number, number, number, number];

export interface ViewState {
  
  zoom: number;  
  panX: number;
  panY: number;
}

export const MIN_ZOOM = 0.02;
export const MAX_ZOOM = 32;

export const IDENTITY: Matrix = [1, 0, 0, 1, 0, 0];

export function applyMatrix(m: Matrix, x: number, y: number): Pt {
  return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
}

export function invertMatrix(m: Matrix): Matrix {
  const det = m[0] * m[3] - m[1] * m[2];
  if (!Number.isFinite(det) || Math.abs(det) < 1e-12) return IDENTITY;
  const a = m[3] / det;
  const b = -m[1] / det;
  const c = -m[2] / det;
  const d = m[0] / det;
  return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])];
}

export function viewMatrix(base: Matrix, view: ViewState): Matrix {
  const z = view.zoom;
  return [base[0] * z, base[1] * z, base[2] * z, base[3] * z, base[4] * z + view.panX, base[5] * z + view.panY];
}

export function toScreen(m: Matrix, p: Pt | number[]): Pt {
  return applyMatrix(m, p[0], p[1]);
}

export function toPdf(m: Matrix, sx: number, sy: number): Pt {
  const [x, y] = applyMatrix(invertMatrix(m), sx, sy);
  return [round4(x), round4(y)];
}

export function round4(v: number): number {
  return Math.round(v * 10000) / 10000;
}

export function clampZoom(z: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));
}

export function fitView(boxW: number, boxH: number, pageW: number, pageH: number, margin = 24): ViewState {
  const zw = (boxW - margin * 2) / Math.max(pageW, 1);
  const zh = (boxH - margin * 2) / Math.max(pageH, 1);
  const zoom = clampZoom(Math.max(0.0001, Math.min(zw, zh)));
  return { zoom, panX: (boxW - pageW * zoom) / 2, panY: (boxH - pageH * zoom) / 2 };
}

export function zoomAt(view: ViewState, cx: number, cy: number, factor: number): ViewState {
  const zoom = clampZoom(view.zoom * factor);
  const k = zoom / view.zoom;
  return { zoom, panX: cx - (cx - view.panX) * k, panY: cy - (cy - view.panY) * k };
}

export function viewForBox(base: Matrix, box: { x0: number; y0: number; x1: number; y1: number }, boxW: number, boxH: number, margin = 80): ViewState {
  const a = applyMatrix(base, box.x0, box.y0);
  const b = applyMatrix(base, box.x1, box.y1);
  const w = Math.max(Math.abs(a[0] - b[0]), 1);
  const h = Math.max(Math.abs(a[1] - b[1]), 1);
  const zoom = clampZoom(Math.min((boxW - margin * 2) / w, (boxH - margin * 2) / h, 8));
  const cx = (a[0] + b[0]) / 2;
  const cy = (a[1] + b[1]) / 2;
  return { zoom, panX: boxW / 2 - cx * zoom, panY: boxH / 2 - cy * zoom };
}

export function pxToPt(px: number, zoom: number): number {
  return px / Math.max(zoom, 1e-9);
}
