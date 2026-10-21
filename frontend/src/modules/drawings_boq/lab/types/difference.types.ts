export type DiffStatus = "SAME" | "CHANGED" | "ADDED" | "REMOVED";
export type VariationKind = "ADDITION" | "OMISSION" | "NEW_ITEM" | "ITEM_DROPPED";
export type FixAudience = "ARCHITECT" | "QS" | "TRACE";

export interface DiffStorey {
  level: string;
  a: number;
  b: number;
  delta: number;
}

export interface DiffMember {
  label?: string;
  key?: string;
  level?: string | null;
  status?: string;
  a: number;
  b: number;
  delta: number;
}

export interface DiffSource {
  source: string;
  a: number;
  b: number;
  delta: number;
}

export interface DiffItem {
  code: string;
  name?: string | null;
  unit: string;
  status: DiffStatus;
  a: number;
  b: number;
  delta: number;
  pct: number | null;
  rows_a?: number;
  rows_b?: number;
  storeys: DiffStorey[];
  members: DiffMember[];
  members_changed: number;
  sources: DiffSource[];
  source_moved: boolean;
}

export interface DiffCause {
  kind: string;
  text: string;
}

export interface VariationLine {
  code: string;
  name?: string | null;
  unit: string;
  kind: VariationKind;
  previous: number;
  revised: number;
  addition: number;
  omission: number;
  pct: number | null;
  basis?: string;
}

export interface Variation {
  lines: VariationLine[];
  counts: Record<string, number>;
  note: string;
  causes?: DiffCause[];
}

export interface DiffMeasures {
  items: number;
  same: number;
  changed: number;
  added: number;
  removed: number;
  source_moved?: number;
  rows_a: number;
  rows_b: number;
}

export interface RunDifference {
  items: DiffItem[];
  measures: DiffMeasures;
  causes: DiffCause[];
  labels: { from: string; to: string };
  from_run?: unknown;
  to_run?: unknown;
  variation: Variation;
}

export interface ComparableRun {
  id: string;
  label: string;
  completed_at?: string | null;
  [key: string]: unknown;
}

export interface FixEntry {
  code: string;
  audience: FixAudience;
  severity: "error" | "warning" | "info" | string;
  topic: string;
  ask: string;
  count: number;
  levels: string[];
  marks: string[];
  [key: string]: unknown;
}

export interface FixList {
  run_id?: string;
  counts: Partial<Record<FixAudience, number>>;
  items: FixEntry[];
  total: number;
  text?: string;
}
