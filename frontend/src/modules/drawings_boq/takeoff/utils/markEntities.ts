import type { MarkChoiceResult, MarkEntity, MarkSource } from "../types/markEntities.types";

const KIND: Record<string, string> = {
  COLUMN: "Column", FOOTING: "Footing", DOOR: "Door", WINDOW: "Window", LINTEL: "Lintel", STAIR: "Stair", BEAM: "Beam", SITE: "Site item",
};

export function kindName(category: string): string {
  return KIND[category] ?? category;
}

export function markTitle(e: MarkEntity): string {
  return `${kindName(e.category)} ${e.tag ?? e.mark}`;
}

const BASIS: Record<string, string> = { SCHEDULE: "schedule", DETAIL: "detail", PLAN: "plan" };

export function sourceLine(s: MarkSource): string {
  if (s.set_aside > 0 && s.open + s.accepted === 0) return `${s.set_aside} set aside`;
  const parts = [`${s.count} shown`];
  if (s.shapes.length > 0) parts.push(s.shapes.map((x) => x.join("×")).join(" or ") + " in");
  if (s.basis) parts.push(`size from ${BASIS[s.basis] ?? s.basis.toLowerCase()}`);
  if (s.accepted > 0) parts.push(`${s.accepted} accepted`);
  return parts.join(" · ");
}

export type MarkTone = "gold" | "green" | "red" | "slate";

export function markState(e: MarkEntity): { tone: MarkTone; text: string } {
  const page = (id: string | null) => e.sources.find((s) => s.sheet_id === id)?.page_no;
  if (e.conflict) return { tone: "red", text: "Accepted from two sheets" };
  if (e.state === "DIFFER") return { tone: "red", text: "The sheets show different counts or sizes: choose one" };
  if (e.state === "DOUBLE") return { tone: "gold", text: `Shown on ${e.live_sheets} sheets with the same count and size: counted again if all are accepted` };
  if (e.state === "UNPLACED") return { tone: "slate", text: e.agree ? "Floor not named on the sheets: check that these are one mark" : "Floor not named on the sheets, and the counts or sizes differ: check that these are one mark" };
  return { tone: "green", text: `Using page ${page(e.chosen_sheet_id)}` };
}

export function markToast(r: MarkChoiceResult): { ok: string; problem: string } {
  const ok = r.chosen.length
    ? `${r.chosen.length} mark${r.chosen.length === 1 ? "" : "s"} settled; ${r.set_aside} items set aside${r.restored ? `, ${r.restored} brought back` : ""}.`
    : "";
  return { ok, problem: r.blocked.map((b) => b.message).join(" ") };
}
