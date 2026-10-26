export type ShadowAgreement = "AGREE" | "DISAGREE" | "AI_ONLY" | "RULE_ONLY";
export type ShadowMode = "WEAK" | "ALL";

export interface ShadowComparison {
  fact_key: string;
  rule_value: string | null;
  ai_value: string | null;
  agreement: ShadowAgreement;
}

export interface ShadowReadItem {
  id: string;
  sheet_id: string;
  page_no: number;
  status: "OK" | "INVALID" | "FAILED";
  mode: ShadowMode;
  prompt_version: string;
  confidence: string | null;
  comparison: ShadowComparison[];
  totals: Record<string, number>;
  problems: string[];
  error: string | null;
  created_at: string;
}

export interface ShadowSummary {
  drawing_id: string;
  enabled: boolean;
  sheets_total: number;
  sheets_read: number;
  totals: Record<ShadowAgreement, number>;
  by_fact: Record<string, Record<ShadowAgreement, number>>;
  items: ShadowReadItem[];
  note: string;
}

export interface ShadowRunResult {
  drawing_id: string;
  mode: ShadowMode;
  read: number;
  failed: number;
  remaining: number;
  items: ShadowReadItem[];
}
