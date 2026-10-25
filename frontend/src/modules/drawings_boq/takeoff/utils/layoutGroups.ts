import type { LayoutChoiceResult, LayoutGroup, LayoutSource } from "../types/layoutGroups.types";

export function groupTitle(g: LayoutGroup): string {
  const pages = g.sources.map((s) => s.page_no).join(", ");
  return `${g.rooms} named rooms, ${g.room_area_m2.toLocaleString("en", { maximumFractionDigits: 1 })} m², on pages ${pages}`;
}

export function sourceLine(s: LayoutSource): string {
  if (s.items === 0) return "nothing read";
  const parts = [`${s.items} items`, `${s.wall_m.toLocaleString("en", { maximumFractionDigits: 1 })} m of wall`];
  if (s.accepted > 0) parts.push(`${s.accepted} accepted`);
  if (s.set_aside) parts.push("set aside");
  else if (s.open > 0) parts.push(`${s.open} open`);
  return parts.join(" · ");
}

export type GroupTone = "gold" | "green" | "red" | "slate";

export function groupState(g: LayoutGroup): { tone: GroupTone; text: string } {
  const page = (id: string | null) => g.sources.find((s) => s.sheet_id === id)?.page_no;
  if (g.kind === "NEAR") return { tone: "slate", text: "Nearly the same: check by eye" };
  if (g.conflict) return { tone: "red", text: "Measured from two sheets" };
  if (g.state === "DOUBLE") return { tone: "gold", text: `Printed ${g.sources.length} times: counted again if all are accepted` };
  if (g.state === "CHOSEN") return { tone: "green", text: `Using page ${page(g.chosen_sheet_id)}` };
  return { tone: "slate", text: "Nothing open" };
}

export function layoutToast(r: LayoutChoiceResult): { ok: string; problem: string } {
  const ok = r.chosen.length
    ? `${r.chosen.map((c) => `page ${c.page_no}`).join(", ")} used; ${r.set_aside} items set aside${r.restored ? `, ${r.restored} brought back` : ""}.`
    : "";
  return { ok, problem: r.blocked.map((b) => b.message).join(" ") };
}
