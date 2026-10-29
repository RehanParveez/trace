export type ConflictKind = "SLAB_THICKNESS" | "BEAM_SECTION" | "SOURCE_COUNT";
export type ConflictPolicy = "STRUCTURAL" | "ARCHITECTURAL" | "LARGER" | "SMALLER" | "AS_READ" | "QS";
export type ConflictDiscipline = "STRUCTURAL" | "ARCHITECTURAL" | "UNKNOWN";

export interface ConflictSource { discipline: ConflictDiscipline | string; page_no: number | null; basis: string }

export interface ConflictValue {
  value_mm: number | null;
  count: number | null;
  label: string;
  mark: string | null;
  steel_text: string | null;
  sources: ConflictSource[];
  quantity: number | null;
  governing: boolean;
  delta: number | null;
  delta_pct: number | null;
}

export interface ValueConflict {
  id: string;
  kind: ConflictKind;
  subject: string;
  floor: string | null;
  attribute: string;
  unit: string;
  item_ids: string[];
  decision: string;
  used_mm: number | null;
  page_no: number | null;
  values: ConflictValue[];
  governing_index: number | null;
  governing_by: "CHOSEN" | "POLICY" | "AS_READ" | null;
  policy: ConflictPolicy | string;
  spread: number;
  spread_pct: number;
  fact_key?: string | null;
  decision_id?: string | null;
}

export interface FactSource { discipline: ConflictDiscipline | string; page_no: number | null; basis: string }

export interface FactOption {
  value: string;
  value_mm: number | null;
  count: number | null;
  mark: string | null;
  label: string | null;
  sources: FactSource[];
  trust: "SCHEDULE" | "DETAIL_OR_SECTION" | "NOTE" | "PLAN" | null;
  default: boolean;
  quantity: number | null;
  unit: string | null;
}

export interface FactDecision {
  id: string;
  kind: ConflictKind | string;
  question: string;
  options: FactOption[];
  chosen: string | null;
  default: string | null;
  open: boolean;
  facts: string[];
  rows: number;
  row_ids: string[];
}

export interface ConflictsResult {
  drawing_id: string;
  conflicts: ValueConflict[];
  policy: Record<string, string>;
  by_kind: Record<string, number>;
  undecided: number;
  decisions?: FactDecision[];
  open_decisions?: number;
}

export interface ResolveConflictsBody {
  policy?: Record<string, string>;
  choices?: Record<string, number>;
  decisions?: Record<string, string>;
  apply_policy?: boolean;
}

export interface ResolveConflictsResult {
  resolved: number;
  items: Array<{ id: string; kind: string; by: string; value: number | null }>;
  skipped: Array<{ id: string; code: string; message: string }>;
  conflicts: ConflictsResult;
}

export type LinkStatus = "LINKED" | "CHOICE" | "PARTLY" | "NOT_LINKED";
export type LinkGroupKey = "BEAM" | "PLINTH_BEAM" | "FOOTING_STRIP" | "FOOTING_PAD" | "NECK_COLUMN" | "COLUMN" | "TANK";

export interface LinkItem {
  id: string;
  group: LinkGroupKey | string;
  tag: string | null;
  label: string | null;
  floor: string | null;
  decision: string;
  status: LinkStatus;
  detail: string | null;
  how: string | null;
  needs: string[];
  reason: string | null;
}

export interface LinkGroup { group: LinkGroupKey | string; total: number; linked: number; choice: number; partly: number; not_linked: number }

export interface LinksResult { drawing_id: string; groups: LinkGroup[]; items: LinkItem[]; truncated: boolean; open: number }

export interface SteelConventions { cover_mm: number; hook_dia: number; lap_dia: number; anchor_dia: number; wastage_pct: number }

export type SteelStatus = "BELOW_RANGE" | "IN_RANGE" | "ABOVE_RANGE" | null;

export interface SteelFamily { marks: number; members: number; kg: number; concrete_m3: number | null; kg_per_m3: number | null; range: [number, number] | null; status: SteelStatus }

export interface SteelMark {
  item_ids: string[];
  tag: string | null;
  category: string;
  family: string;
  floor: string | null;
  count: number;
  decision: string;
  steel_text: string | null;
  source: string;
  kg_each: number;
  kg: number;
  concrete_m3: number | null;
}

export interface SteelRollup {
  drawing_id: string;
  ran: boolean;
  kg: number;
  conventions: SteelConventions;
  conventions_assumed: boolean;
  convention_note: string;
  by_family: Record<string, SteelFamily>;
  by_diameter: Record<string, { kg: number; length_m: number }>;
  marks: SteelMark[];
  without_steel: { members: number; by_family: Record<string, { members: number; marks: string[] }> };
  without_size: number;
  unprinted?: import("../../utils/steelEstimate").UnprintedSteel;
}

export interface CombineResult {
  chosen: Array<{ floor: string; sheet_id: string; page_no: number; other_page_no?: number; combined?: boolean; same?: number; added?: number; set_aside: number; restored: number }>;
  set_aside: number;
  restored: number;
  blocked: Array<{ floor: string; code: string; message: string }>;
  floors: import("./takeoff.types").FloorSources;
}
