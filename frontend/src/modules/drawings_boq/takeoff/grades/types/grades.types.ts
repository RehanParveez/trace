export type GradeHow = "NAMED" | "GENERAL" | "PCC" | "NONE";

export interface ConcreteRule {
  value: string;
  label: string;
  class: string | null;
  mix: string;
  scope: string;
  members: string[];
  how: GradeHow;
  text: string | null;
  pages: number[];
  count: number;
}

export interface SteelRule {
  value: string;
  label: string;
  grade: number;
  scope: string;
  members: string[];
  how: GradeHow;
  text: string | null;
  pages: number[];
  count: number;
}

export interface MemberConcrete {
  class: string | null;
  mix: string;
  scope: string;
  pages: number[];
}

export interface MemberSteel {
  label: string;
  scope: string;
  pages: number[];
}

export interface GradeMember {
  member: string;
  label: string;
  found: number;
  measured: number;
  stamped: number;
  typed: number;
  open: number;
  confirmed_open: number;
  concrete: MemberConcrete | null;
  concrete_clash: string[];
  steel: MemberSteel | null;
  steel_clash: string[];
}

export interface GradeMix {
  what: string;
  grade: string;
  pages: number[];
  found: number;
  measured: number;
  stamped: number;
  typed: number;
  open: number;
  confirmed_open: number;
}

export interface PrintedNote {
  text: string | null;
  pages: number[];
  count: number;
}

export interface PlasterInfo {
  thickness_mm: number | null;
  note: PrintedNote | null;
}

export interface SoilNote extends PrintedNote {
  cement_pct: number;
  depth_mm: number | null;
  loose_only: boolean;
}

export interface SoilInfo {
  notes: SoilNote[];
  cement_pct: number | null;
  depth_mm: number | null;
}

export interface GradesSummary {
  mix_notes?: number;
  concrete_notes?: number;
  steel_notes?: number;
  measured?: number;
  stamped?: number;
  typed?: number;
  open?: number;
  confirmed_open?: number;
  clashes?: number;
}

export interface GradesConflict {
  param: string;
  values?: { value?: number; value_mm?: number }[];
}

export interface GradesReport {
  drawing_id: string;
  concrete: ConcreteRule[];
  steel: SteelRule[];
  members: GradeMember[];
  mixes: GradeMix[];
  plaster: PlasterInfo;
  soil: SoilInfo | null;
  conflicts: GradesConflict[];
  summary: GradesSummary;
  changed: number;
}

export interface StampBody {
  include_confirmed: boolean;
}
