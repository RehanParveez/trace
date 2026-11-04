export type SteelFiguresSource = "BBS_AUDITED" | "BBS_WEIGHT" | "RULE_ESTIMATE";
export type SteelFormula = "REBAR_BBS_WEIGHT" | "REBAR_BBS_AUDITED" | "REBAR_RULE_ESTIMATE";

export interface SteelFigure {
  formula: SteelFormula;
  kg: string | null;
  origin: string | null;
  note: string | null;
  applied_count: number | null;
  applied_kg: string | null;
  signed_count: number | null;
}

export interface SteelFiguresLine {
  formula: SteelFormula | null;
  source: SteelFiguresSource | null;
  quantity_kg: string | null;
  unit: string;
  note: string;
  audited: boolean;
}

export interface SteelOpenFindings {
  count: number;
  by_class: Record<string, number>;
  by_code: Record<string, number>;
  effect_kg: string;
}

export interface SteelDiameter {
  dia: number;
  label: string;
  mm: string | null;
  bbs_kg: string;
  applied_kg: string;
  audited_kg: string;
}

export interface SteelWastage {
  pct: string;
  kg: string | null;
  total_kg: string | null;
}

export interface SteelDocument {
  document_id: string;
  file_name: string | null;
  version: number;
  run_id: string | null;
  run_level: string | null;
  run_created_at: string | null;
}

export interface SteelFigures {
  figures: Record<SteelFormula, SteelFigure>;
  requested_source: SteelFiguresSource | null;
  source: SteelFiguresSource | null;
  fell_back_from: SteelFiguresSource | null;
  line: SteelFiguresLine;
  open_findings: SteelOpenFindings;
  by_diameter: SteelDiameter[];
  unattributed_kg: string | null;
  allocated_kg: string | null;
  wastage: SteelWastage | null;
  ledger_gap_kg: string | null;
  ledger_bbs_kg: string | null;
  document: SteelDocument | null;
  has_document: boolean;
  has_audit: boolean;
  run_id: string;
  project_id: string;
  sources: SteelFiguresSource[];
}

export interface SteelSourceChoice {
  project_id: string;
  source: SteelFiguresSource | null;
  sources: SteelFiguresSource[];
}
