import type { CountGeometry, TakeoffMeasurement } from "../types/takeoff.types";

export function tagTally(measurements: TakeoffMeasurement[], tag: string): { confirmed: number; draft: number } {
  let confirmed = 0;
  let draft = 0;
  for (const m of measurements) {
    if (m.kind !== "COUNT" || (m.tag ?? "").trim().toUpperCase() !== tag.trim().toUpperCase()) continue;
    const n = (m.geometry as CountGeometry).points?.length ?? 0;
    if (m.status === "CONFIRMED") confirmed += n;
    else draft += n;
  }
  return { confirmed, draft };
}