export interface RuleDraft {
  id: string;
  key: string;
  scope: Record<string, unknown>;
  value: unknown;
  unit: string | null;
  cls: string | null;
  source: { workbook?: string; sheet?: string; cell?: string; text?: string; map_cell?: string; cells?: string[] };
  note: string | null;
  needs: string[];
  seed: { key: string; value: unknown; same: boolean; compares?: string } | null;
  confirmable: boolean;
  why_not: string | null;
  confirmed_by: string | null;
}

export interface RuleDrafts { drafts: RuleDraft[] }

export interface DraftFile { workbook?: string; rules: Array<Record<string, unknown>> }
