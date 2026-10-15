import { create } from "zustand";
import type { MeasureKind, MeasureSource, Pt, SnapKind } from "../types/takeoff.types";

export type Tool = "select" | "pan" | "ruler" | "calibrate" | "length" | "area" | "count" | "wall" | "room";
export type PanelTab = "measure" | "list" | "scale" | "counts" | "results" | "frame" | "found";

export interface Draft {
  kind: MeasureKind;
  points: Pt[];
  snapped: boolean[];
  closed: boolean;
  holes: Pt[][];
  holeSnapped: boolean[][];
  activeHole: number | null;
  origin: { source: MeasureSource; tag?: string | null; label?: string | null; wallThicknessMm?: number | null } | null;
}

export function emptyDraft(kind: MeasureKind): Draft {
  return { kind, points: [], snapped: [], closed: false, holes: [], holeSnapped: [], activeHole: null, origin: null };
}

interface TakeoffViewState {
  tool: Tool;
  tab: PanelTab;
  snapOn: boolean;
  snapKinds: SnapKind[];
  showMeasurements: boolean;
  showDimensions: boolean;
  orthoLock: boolean;
  draft: Draft | null;
  selectedIds: string[];
  focusId: string | null;
  setTool: (tool: Tool) => void;
  setTab: (tab: PanelTab) => void;
  toggleSnap: () => void;
  toggleSnapKind: (kind: SnapKind) => void;
  toggleMeasurements: () => void;
  toggleDimensions: () => void;
  setOrtho: (on: boolean) => void;
  setDraft: (draft: Draft | null) => void;
  addPoint: (p: Pt, snapped: boolean) => void;
  removeLastPoint: () => void;
  closeRing: () => void;
  startHole: () => void;
  finishHole: () => void;
  select: (ids: string[]) => void;
  focus: (id: string | null) => void;
  reset: () => void;
}

const ALL_KINDS: SnapKind[] = ["ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE"];

export const useTakeoffView = create<TakeoffViewState>((set, get) => ({
  tool: "select",
  tab: "scale",
  snapOn: true,
  snapKinds: ALL_KINDS,
  showMeasurements: true,
  showDimensions: false,
  orthoLock: false,
  draft: null,
  selectedIds: [],
  focusId: null,
  setTool: (tool) => {
    const current = get().draft;
    const next: Partial<TakeoffViewState> = { tool };

    if (current && !current.origin) next.draft = null;
    if (tool === "length") next.draft = current && current.kind === "LENGTH" && !current.origin ? current : emptyDraft("LENGTH");
    else if (tool === "area") next.draft = current && current.kind === "AREA" && !current.origin ? current : emptyDraft("AREA");
    else if (tool === "count") next.draft = current && current.kind === "COUNT" && !current.origin ? current : emptyDraft("COUNT");
    if (tool === "length" || tool === "area" || tool === "count") next.tab = "measure";
    set(next as TakeoffViewState);
  },
  setTab: (tab) => set({ tab }),
  toggleSnap: () => set((s) => ({ snapOn: !s.snapOn })),
  toggleSnapKind: (kind) => set((s) => ({ snapKinds: s.snapKinds.includes(kind) ? s.snapKinds.filter((k) => k !== kind) : [...s.snapKinds, kind] })),
  toggleMeasurements: () => set((s) => ({ showMeasurements: !s.showMeasurements })),
  toggleDimensions: () => set((s) => ({ showDimensions: !s.showDimensions })),
  setOrtho: (on) => set({ orthoLock: on }),
  setDraft: (draft) => set({ draft }),
  addPoint: (p, snapped) =>
    set((s) => {
      const d = s.draft;
      if (!d) return {};
      if (d.activeHole !== null) {
        const holes = d.holes.map((h) => h.slice());
        const hs = d.holeSnapped.map((h) => h.slice());
        holes[d.activeHole].push(p);
        hs[d.activeHole].push(snapped);
        return { draft: { ...d, holes, holeSnapped: hs } };
      }
      return { draft: { ...d, points: [...d.points, p], snapped: [...d.snapped, snapped] } };
    }),
  removeLastPoint: () =>
    set((s) => {
      const d = s.draft;
      if (!d) return {};
      if (d.activeHole !== null) {
        const holes = d.holes.map((h) => h.slice());
        const hs = d.holeSnapped.map((h) => h.slice());
        if (holes[d.activeHole].length > 0) {
          holes[d.activeHole].pop();
          hs[d.activeHole].pop();
          return { draft: { ...d, holes, holeSnapped: hs } };
        }
        holes.pop();
        hs.pop();
        return { draft: { ...d, holes, holeSnapped: hs, activeHole: null } };
      }
      return { draft: { ...d, points: d.points.slice(0, -1), snapped: d.snapped.slice(0, -1), closed: false } };
    }),
  closeRing: () => set((s) => (s.draft ? { draft: { ...s.draft, closed: true } } : {})),
  startHole: () =>
    set((s) => (s.draft && s.draft.kind === "AREA" && s.draft.points.length >= 3
      ? { draft: { ...s.draft, holes: [...s.draft.holes, []], holeSnapped: [...s.draft.holeSnapped, []], activeHole: s.draft.holes.length } }
      : {})),
  finishHole: () =>
    set((s) => {
      const d = s.draft;
      if (!d || d.activeHole === null) return {};
      const hole = d.holes[d.activeHole];
      if (hole.length < 3) {
        return { draft: { ...d, holes: d.holes.slice(0, -1), holeSnapped: d.holeSnapped.slice(0, -1), activeHole: null } };
      }
      return { draft: { ...d, activeHole: null } };
    }),
  select: (ids) => set({ selectedIds: ids }),
  focus: (id) => set({ focusId: id }),
  reset: () => set({ tool: "select", tab: "scale", draft: null, selectedIds: [], focusId: null, showDimensions: false }),
}));
