import type { Frame, FrameMember, FrameView } from "../types/takeoff.types";

export const VIEW_COLORS = ["#2563eb", "#d97706", "#059669", "#9333ea", "#dc2626", "#0891b2", "#65a30d", "#db2777"];

export interface Box { x0: number; y0: number; x1: number; y1: number }
export interface Fit { scale: number; x0: number; y1: number; pad: number }

export function viewColor(index: number): string {
  return VIEW_COLORS[((index % VIEW_COLORS.length) + VIEW_COLORS.length) % VIEW_COLORS.length];
}

export function memberBox(m: FrameMember, dx = 0, dy = 0): Box | null {
  if (m.x_mm === null || m.y_mm === null) return null;
  const x = m.x_mm + dx, y = m.y_mm + dy;
  return { x0: x - m.length_mm / 2, y0: y - m.width_mm / 2, x1: x + m.length_mm / 2, y1: y + m.width_mm / 2 };
}

export function frameBounds(frame: Frame, nudges: Record<string, [number, number]> = {}): Box | null {
  let b: Box | null = null;
  for (const v of frame.views) {
    const [dx, dy] = nudges[v.key] ?? [0, 0];
    for (const m of v.members) {
      const mb = memberBox(m, dx, dy);
      if (!mb) continue;
      b = b ? { x0: Math.min(b.x0, mb.x0), y0: Math.min(b.y0, mb.y0), x1: Math.max(b.x1, mb.x1), y1: Math.max(b.y1, mb.y1) } : mb;
    }
  }
  return b;
}

export function fitTo(bounds: Box, width: number, height: number, pad = 12): Fit {
  const w = Math.max(bounds.x1 - bounds.x0, 1), h = Math.max(bounds.y1 - bounds.y0, 1);
  const scale = Math.min((width - 2 * pad) / w, (height - 2 * pad) / h);
  return { scale: scale > 0 ? scale : 1, x0: bounds.x0, y1: bounds.y1, pad };
}

export function toScreen(fit: Fit, box: Box): { x: number; y: number; w: number; h: number } {
  return { x: fit.pad + (box.x0 - fit.x0) * fit.scale, y: fit.pad + (fit.y1 - box.y1) * fit.scale, w: (box.x1 - box.x0) * fit.scale, h: (box.y1 - box.y0) * fit.scale };
}

export type ViewState = "UNPLACED" | "GUESS" | "DONE";

export function viewState(v: FrameView): ViewState {
  if (v.method === "UNALIGNED" && !v.decided) return "UNPLACED";
  return v.grade === "CONFIRMED" || v.decided ? "DONE" : "GUESS";
}

export function methodLabel(v: FrameView): string {
  switch (v.method) {
    case "REFERENCE": return "Reference view";
    case "COLUMN_MATCH": return `Matched ${v.supporters} of ${v.compared} columns`;
    case "ENVELOPE": return "Placed by outline only";
    case "MANUAL": return "Placed by hand";
    default: return "Not placed";
  }
}

export function addNudge(current: [number, number] | undefined, ddx: number, ddy: number): [number, number] {
  const [x, y] = current ?? [0, 0];
  return [Math.round((x + ddx) * 100) / 100, Math.round((y + ddy) * 100) / 100];
}

export function shiftToSave(v: FrameView, nudge: [number, number] | undefined): [number, number] {
  const [dx, dy] = nudge ?? [0, 0];
  return [Math.round((v.dx_mm + dx) * 100) / 100, Math.round((v.dy_mm + dy) * 100) / 100];
}

export function openCount(frame: Frame): number {
  return frame.views.filter((v) => viewState(v) !== "DONE").length;
}
