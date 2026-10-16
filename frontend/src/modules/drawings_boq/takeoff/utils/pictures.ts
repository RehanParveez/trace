import type { BeamSectionRead, DrawingFacts, PictureReadState, TankDrawingRead, TankSizeRead } from "../types/takeoff.types";

export type PictureSource = "TEXT" | "PICTURE" | "BOTH" | "NOT_READ" | "TIMEOUT";

export function pictureSource(read: PictureReadState): PictureSource {
  if (read === "TEXT") return "TEXT";
  if (read === "TEXT+OCR") return "BOTH";
  if (read === "OCR") return "PICTURE";
  if (read === "TIMEOUT") return "TIMEOUT";
  return "NOT_READ";
}

export function beamRows(facts: DrawingFacts | undefined): BeamSectionRead[] {
  return [...(facts?.beam_details ?? [])].sort((a, b) => String(a.mark ?? "").localeCompare(String(b.mark ?? ""), undefined, { numeric: true }) || (a.page_no ?? 0) - (b.page_no ?? 0));
}

export function tankRows(facts: DrawingFacts | undefined): TankDrawingRead[] {
  return [...(facts?.tank_details ?? [])].sort((a, b) => String(a.kind ?? "").localeCompare(String(b.kind ?? "")) || String(a.view ?? "").localeCompare(String(b.view ?? "")) || (a.page_no ?? 0) - (b.page_no ?? 0));
}

export function hasPictureReads(facts: DrawingFacts | undefined): boolean {
  return (facts?.beam_details?.length ?? 0) > 0 || (facts?.tank_details?.length ?? 0) > 0;
}

export function pictureReaderMissing(facts: DrawingFacts | undefined): boolean {
  if (!hasPictureReads(facts) || facts?.picture_reader == null || facts.picture_reader.usable) return false;
  const needs = (r: PictureReadState) => r !== "TEXT" && r !== "TEXT+OCR" && r !== "OCR";
  return (facts.beam_details ?? []).some((d) => needs(d.read)) || (facts.tank_details ?? []).some((d) => needs(d.read));
}

export function beamText(d: BeamSectionRead): string {
  const parts: string[] = [];
  if (d.depth_in != null) parts.push(`${Math.round(d.depth_in * 10) / 10}" deep`);
  if (d.steel_text) parts.push(d.steel_text);
  return parts.join(" · ");
}

export function tankSizeText(s: TankSizeRead): string {
  return s.source === "TEXT" ? `${s.text}` : `${s.text} (${s.votes ?? 0}×)`;
}

export function tankSizes(d: TankDrawingRead): TankSizeRead[] {
  return [...d.sizes].sort((a, b) => Number(b.source === "TEXT") - Number(a.source === "TEXT") || (b.votes ?? 0) - (a.votes ?? 0));
}

export function sourceLabel(s: PictureSource): string {
  switch (s) {
    case "TEXT": return "PDF text";
    case "BOTH": return "PDF text and picture";
    case "PICTURE": return "picture";
    case "TIMEOUT": return "ran out of time";
    default: return "not read";
  }
}
