import type { Drawing } from "../../types/drawings-boq.types";
import type { ProjectTakeoffDrawing } from "../types/takeoff.types";

export interface WaitingPdf { drawing: Drawing; row: ProjectTakeoffDrawing }

export interface RunDrawings {
  eligible: Drawing[];
  waiting: WaitingPdf[];
  takeoff: Record<string, { confirmed: number; draft: number }>;
}

export function runDrawings(drawings: Drawing[], takeoff: ProjectTakeoffDrawing[]): RunDrawings {
  const rows = new Map(takeoff.map((r) => [r.drawing_id, r]));
  const eligible: Drawing[] = [];
  const waiting: WaitingPdf[] = [];
  const counts: RunDrawings["takeoff"] = {};
  for (const drawing of drawings) {
    if (!drawing.is_current_revision) continue;
    if (drawing.format === "IFC") {
      if (drawing.status === "PARSED") eligible.push(drawing);
      continue;
    }
    if (drawing.format !== "PDF") continue;
    const row = rows.get(drawing.id);
    if (!row || row.sheets === 0) continue;
    counts[drawing.id] = { confirmed: row.confirmed, draft: row.draft };
    if (row.confirmed > 0) eligible.push(drawing);
    else waiting.push({ drawing, row });
  }
  return { eligible, waiting, takeoff: counts };
}
