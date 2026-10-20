import type { LedgerTrace, OneTotalDecision, OneTotalStats, PdfTakeoffStats } from "../types/drawings-boq.types";

export const KIND_WORDS: Record<string, string> = {
  COLUMN: "Columns",
  FOOTING: "Footings",
  BEAM: "Beams and lintels",
  SLAB: "Slabs",
  STAIR: "Stairs",
};

export function kindWords(kind: string): string {
  return KIND_WORDS[kind] ?? kind;
}

export function oneTotalReasonWords(reason: string | null | undefined): string {
  switch (reason) {
    case "NO_DRAWING_MEMBERS":
      return "No counted member (a mark with a count and a size) was read from a drawing, so there was nothing to set against the model.";
    case "NO_MODEL_ELEMENTS":
      return "The run had no model elements to match against.";
    default:
      return reason ?? "";
  }
}

export function decisionWords(reason: string | null | undefined): string {
  switch (reason) {
    case "MODEL_MORE_EXACT":
      return "The model's quantity has the narrower range, so it was kept.";
    case "DRAWING_MORE_EXACT":
      return "The drawing's quantity has the narrower range, so it was kept.";
    case "TIE_DRAWING":
      return "Both have the same range; the drawing was kept.";
    case "CHOICE_DRAWING":
      return "The setting keeps the drawing.";
    case "CHOICE_MODEL":
      return "The setting keeps the model.";
    case "PARTIAL_DRAWING_COVERS_ALL":
      return "Only some of the members were found in the model. The drawing says how many there are, so its mark was kept whole and the model's partners were set aside.";
    case "MATCHING_NOT_TRUSTED":
      return "Too few members of this kind found a partner, so names and positions cannot be trusted here. The model was kept and the drawing set aside, as before.";
    default:
      return reason ?? "";
  }
}

export function drawingOnlyWords(why: string | null | undefined): string {
  switch (why) {
    case "NO_MODEL_MEMBER":
      return "The model has no member of this kind here.";
    case "NO_PARTNER_IN_MODEL":
      return "The model has members of this kind here, but none of them is this one.";
    default:
      return why ?? "";
  }
}

export function matchWords(by: string | null | undefined): string {
  switch (by) {
    case "MARK":
      return "same mark";
    case "POSITION":
      return "same place";
    case "MARK+POSITION":
      return "same mark and place";
    case "MIXED":
      return "mark or place";
    default:
      return "";
  }
}

export function preferWords(prefer: string | null | undefined): string {
  switch (prefer) {
    case "DRAWING":
      return "the drawing";
    case "MODEL":
      return "the model";
    default:
      return "the more exact source";
  }
}

export interface KindTotalView {
  kind: string;
  label: string;
  modelM3: string;
  drawingM3: string;
  totalM3: string;
  lowM3: string;
  highM3: string;
  bounded: boolean;
}

export interface OneTotalView {
  ran: boolean;
  reason: string | null;
  prefer: string;
  toleranceWords: string;
  positionToleranceMm: number | null;
  trustedSharePct: number | null;
  complete: number;
  partial: number;
  setAside: number;
  conflictsTotal: number;
  drawingOnlyMarks: number;
  modelOnlyMembers: number;
  usedModel: number;
  usedDrawing: number;
  truncated: boolean;
  kinds: KindTotalView[];
  conflicts: OneTotalDecision[];
  drawingOnly: { tag: string; kind: string; members: number; m3: string; why: string }[];
  modelOnly: { mark: string; kind: string; m3: string; elementId: string }[];
  notTrusted: { kind: string; drawingMembers: number; modelMembers: number; matched: number; sharePct: number }[];
  alignments: { group: string; method: string; supporters: number; compared: number }[];
}

export function oneTotalView(takeoff: PdfTakeoffStats | OneTotalStats | null | undefined): OneTotalView | null {
  const stats: OneTotalStats | undefined = takeoff && "one_total" in (takeoff as PdfTakeoffStats) ? (takeoff as PdfTakeoffStats).one_total : (takeoff as OneTotalStats | undefined);
  if (!stats || !stats.enabled) return null;
  const totals = stats.totals ?? {};
  return {
    ran: Boolean(stats.ran),
    reason: stats.reason ?? null,
    prefer: preferWords(stats.prefer),
    toleranceWords: stats.tolerance_pct ? `${stats.tolerance_pct} percent` : "",
    positionToleranceMm: stats.position_tolerance_mm ?? null,
    trustedSharePct: stats.trusted_share_pct ?? null,
    complete: Number(stats.complete ?? 0),
    partial: Number(stats.partial ?? 0),
    setAside: Number(stats.set_aside_not_matched ?? 0),
    conflictsTotal: Number(stats.conflicts_total ?? 0),
    drawingOnlyMarks: Number(stats.drawing_only_marks ?? 0),
    modelOnlyMembers: Number(stats.model_only_members ?? 0),
    usedModel: Number(stats.used_model ?? 0),
    usedDrawing: Number(stats.used_drawing ?? 0),
    truncated: Boolean(stats.truncated),
    kinds: Object.entries(totals)
      .map(([kind, t]) => ({
        kind, label: kindWords(kind), modelM3: t.model_m3, drawingM3: t.drawing_m3, totalM3: t.total_m3, lowM3: t.low_m3, highM3: t.high_m3, bounded: Boolean(t.bounded),
      }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    conflicts: stats.conflicts ?? [],
    drawingOnly: (stats.drawing_only ?? []).map((d) => ({ tag: d.tag ?? "—", kind: kindWords(d.category), members: d.members, m3: d.drawing_m3, why: drawingOnlyWords(d.why) })),
    modelOnly: (stats.model_only ?? []).map((m) => ({ mark: m.mark ?? "—", kind: kindWords(m.category), m3: m.model_m3, elementId: m.element_id })),
    notTrusted: (stats.not_trusted ?? []).map((n) => ({ kind: kindWords(n.category), drawingMembers: n.drawing_members, modelMembers: n.model_members, matched: n.matched, sharePct: n.share_pct })),
    alignments: (stats.alignment ?? []).map((a) => ({ group: a.group, method: a.method, supporters: Number(a.supporters ?? 0), compared: Number(a.compared ?? 0) })),
  };
}

export type SourceTone = "blue" | "gold" | "slate" | "green" | "red";

export interface SourceView {
  label: string;
  tone: SourceTone;
  note: string | null;
}

const SOURCE: Record<string, { label: string; tone: SourceTone }> = {
  MODEL: { label: "Model", tone: "blue" },
  PDF_TAKEOFF: { label: "Drawing", tone: "gold" },
  DERIVED: { label: "Derived", tone: "slate" },
  SCHEDULE_IMPORT: { label: "Schedule", tone: "slate" },
  MANUAL: { label: "Typed", tone: "green" },
  ESTIMATE: { label: "Estimate", tone: "red" },
};

export function sourceView(kind: string, trace?: LedgerTrace | null): SourceView {
  const base = SOURCE[kind] ?? { label: kind, tone: "slate" as SourceTone };
  const note = (trace?.inputs as Record<string, unknown> | undefined)?.one_total as
    | { state?: string; difference_pct?: string | null; model_m3?: string | null; conflict?: boolean; reason?: string }
    | undefined;
  if (!note) return { ...base, note: null };
  const diff = note.difference_pct != null && note.conflict ? ` The model gives ${note.model_m3} m³ (${Number(note.difference_pct) > 0 ? "+" : ""}${note.difference_pct} percent against it).` : "";
  return { ...base, note: `Kept over the model's quantity for the same member${note.state === "PARTIAL" ? ", whole mark" : ""}.${diff}` };
}
