import type { ColumnReconcile, ReconcileModelPlace, ReconcilePdfPlace, ReconcileQuery } from "../types/takeoff.types";

export type ReconcileState = "EMPTY" | "NO_MODEL" | "NO_PDF" | "UNMATCHED" | "AGREES" | "DIFFERS";

export function reconcileState(r: ColumnReconcile | undefined): ReconcileState {
  if (!r) return "EMPTY";
  if (r.status === "NONE") return r.reason === "NO_MODEL" ? "NO_MODEL" : "NO_PDF";
  if (r.status === "UNMATCHED") return "UNMATCHED";
  return r.agrees ? "AGREES" : "DIFFERS";
}

export function pdfPlaceText(p: ReconcilePdfPlace): string {
  const marks = p.marks.length ? p.marks.join(", ") : "no mark";
  return `${marks} (${p.views.join(", ")})`;
}

export function modelPlaceText(p: ReconcileModelPlace): string {
  return p.names.length ? p.names.join(", ") : "unnamed column";
}

export function sizeText(s: number[] | null): string {
  return s && s.length === 2 ? `${Math.round(s[0])} × ${Math.round(s[1])} mm` : "size not known";
}

export function placementText(r: ColumnReconcile): string {
  const shift = `dx ${Math.round(r.dx_mm)} mm, dy ${Math.round(r.dy_mm)} mm`;
  if (r.method === "GIVEN") return `Placed by the shift you gave (${shift}).`;
  return `Placed by matching ${r.supporters} of ${r.compared} columns (${shift}). This is an assumption until you give the shift.`;
}

export function shiftQuery(model: string | null, dx: string, dy: string): ReconcileQuery {
  const q: ReconcileQuery = {};
  if (model) q.model_drawing_id = model;
  const x = Number(dx.trim().replace(/,/g, "")), y = Number(dy.trim().replace(/,/g, ""));
  if (dx.trim() !== "" && dy.trim() !== "" && Number.isFinite(x) && Number.isFinite(y) && Math.abs(x) <= 1_000_000 && Math.abs(y) <= 1_000_000) {
    q.dx_mm = x;
    q.dy_mm = y;
  }
  return q;
}
