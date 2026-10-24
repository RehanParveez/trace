export interface DecisionFigure {
  key: string;
  value: number;
  unit: string;
}

export interface DecisionEffect {
  figures: DecisionFigure[];
  diff: number | null;
  diff_unit: string;
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

export interface DecisionsReport {
  drawing_id: string;
  items: DecisionItem[];
  stale_pages: number[];
  sheets_read: number;
}

export interface ChooseDecisionBody {
  key: string;
  value: string | null;
}
