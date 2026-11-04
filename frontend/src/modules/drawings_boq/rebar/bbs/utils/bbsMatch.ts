import type { AskGroup, ConfirmPayload, MatchItem, MatchKind, MatchRun } from "../types/bbsMatch.types";

export const FLOORS = ["BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "ROOF", "MUMTY"] as const;
export const GATE_SHARE = 0.95;
export const KIND_ORDER: MatchKind[] = ["ASK", "EXTRA", "MISSING", "MATCH"];
export const CLASSES = ["COLUMN", "BEAM", "FOOTING", "PLINTH", "LINTEL", "SLAB", "TANK", "OTHER"] as const;
const NOTE_MAX = 500;

export function kindTone(kind: string): "red" | "gold" | "blue" | "green" {
  if (kind === "ASK") return "gold";
  if (kind === "EXTRA" || kind === "MISSING") return "red";
  return "green";
}

export function sharePercent(share: number | undefined): string {
  if (share === undefined || !Number.isFinite(share)) return "—";
  return `${(share * 100).toFixed(1)}%`;
}

export function gateMet(run: MatchRun | null | undefined): boolean {
  return Boolean(run) && (run as MatchRun).stats.share_without_asking >= GATE_SHARE;
}

export function methodLabel(method: string | null): string {
  switch (method) {
    case "FAMILY_MARK": return "Mark";
    case "ROOM_PANEL": return "Room";
    case "SHEET_ONLY": return "Sheet only";
    case "USER": return "Confirmed";
    default: return "—";
  }
}

export function elementLabel(e: { class: string; mark: string | null; floor: string | null }): string {
  const parts = [e.mark ?? e.class];
  if (e.floor) parts.push(e.floor.toLowerCase());
  return parts.join(" · ");
}

export function itemWhere(i: Pick<MatchItem, "sheet_name" | "member">): string {
  return [i.sheet_name, i.member].filter(Boolean).join(" · ") || "—";
}

export function floorMapChanged(current: Record<string, string[]>, edited: Record<string, string[]>): boolean {
  const names = new Set([...Object.keys(current), ...Object.keys(edited)]);
  for (const n of names) {
    if ((current[n] ?? []).join("|") !== (edited[n] ?? []).join("|")) return true;
  }
  return false;
}

export function orderedFloorMap(map: Record<string, string[]>): Array<[string, string[]]> {
  return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
}

export function confirmProblem(cls: string, mark: string, floor: string, reviewedOnly: boolean, note: string): string | null {
  if (note.length > NOTE_MAX) return "note-too-long";
  if (reviewedOnly) return note.trim() ? null : "note-needed";
  if (!cls) return "class-needed";
  if (!mark.trim()) return "mark-needed";
  if (floor && !(FLOORS as readonly string[]).includes(floor)) return "floor-unknown";
  return null;
}

export function confirmPayload(group: AskGroup, cls: string, mark: string, floor: string, reviewedOnly: boolean, note: string): ConfirmPayload {
  const cleanNote = note.trim() || null;
  if (reviewedOnly) return { group: group.group, elements: [], note: cleanNote };
  return { group: group.group, elements: [{ class: cls, mark: mark.trim(), floor: floor || null }], note: cleanNote };
}

export function sortedFamilies(stats: MatchRun["stats"] | undefined): Array<[string, number, number]> {
  return Object.entries(stats?.by_family ?? {}).map(([f, v]): [string, number, number] => [f, v.matched, v.rows]).sort((a, b) => a[0].localeCompare(b[0]));
}
