export interface DecisionFigure {
  key: string;
  value: number;
  unit: string;
}

export interface DecisionEffect {
  figures: DecisionFigure[];
  diff: number | null;
  diff_unit: string;
  diffs?: DecisionFigure[];
}

export interface DecisionOption {
  value: string;
  label: string;
  text: string;
  is_default: boolean;
  in_force: boolean;
  effect: DecisionEffect | null;
}

export interface DecisionItem {
  key: string;
  rule: string;
  kind: "CHOICE" | "SWITCH";
  title: string;
  question: string;
  affects: string;
  default: string;
  current: string;
  made_by_person: boolean;
  made_at: string | null;
  applies: boolean;
  walls: number;
  floors: string[];
  options: DecisionOption[];
  stale_pages: number[];
  accepted_stale: number;
}

export interface FactDecisionOption {
  value: string;
  label: string | null;
  trust: string | null;
  default: boolean;
  quantity: number | null;
  unit: string | null;
  sources: Array<{ discipline: string; page_no: number | null; basis: string }>;
}

export interface FactDecisionItem {
  id: string;
  kind: string;
  title: string;
  question: string;
  affects: string;
  tolerance: number;
  unit: string;
  facts: string[];
  rows: number;
  default: string | null;
  chosen: string | null;
  open: boolean;
  options: FactDecisionOption[];
}

export interface SheetDecisionOption {
  value: string;
  label: string;
  text: string;
  pages: number[];
  sheet_ids: string[];
  items: number;
  open: number;
  accepted: number;
  set_aside: boolean;
  live: number;
  sample: { id: string; label: string | null; geometry: unknown } | null;
}

export interface SheetDecision {
  id: string;
  kind: "OPTION" | "REVISION";
  caption: string;
  floor: string | null;
  sheet_no: string | null;
  question: string;
  state: "OPEN" | "CHOSEN" | "NONE";
  default: string | null;
  chosen: string | null;
  choosable: boolean;
  options: SheetDecisionOption[];
}

export interface DecisionsReport {
  drawing_id: string;
  items: DecisionItem[];
  sheets?: SheetDecision[];
  facts?: FactDecisionItem[];
  stale_pages: number[];
  sheets_read: number;
}

export interface ChooseDecisionBody {
  key: string;
  decision_id?: string;
  value: string | null;
}
