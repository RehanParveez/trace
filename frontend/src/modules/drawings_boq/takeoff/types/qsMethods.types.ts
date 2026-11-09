export type QsMethodState = "IN_FORCE" | "SAME_AS_TRACE" | "WOULD_CHANGE" | "YOURS" | "NOT_SETTABLE";

export type QsMethodAspect = "deductions" | "faces" | "heights" | "laps" | "wastage" | "working_space" | "projections";

export interface QsMethodRow {
  id: string;
  aspect: QsMethodAspect;
  item: string;
  says: string;
  key: string;
  scope: Record<string, unknown>;
  value: unknown;
  trace_value: unknown;
  held_value: unknown;
  held_origin: string | null;
  state: QsMethodState;
  source: string;
  confirmed: boolean;
}

export interface QsOpenQuestion {
  id: string;
  aspect: QsMethodAspect;
  item: string;
  question: string;
  trace: string;
  standard: string | null;
  asked: string | null;
}

export interface QsMethodProfile {
  id: string;
  label: string;
  qs: string;
  chosen: boolean;
  methods: QsMethodRow[];
  would_change: number;
  same_as_trace: number;
  kept: number;
  not_settable: number;
  unconfirmed: number;
}

export interface QsMethods {
  chosen: string | null;
  profiles: QsMethodProfile[];
  open_questions: QsOpenQuestion[];
}

export interface QsMethodChoice {
  profile: string | null;
  note?: string | null;
}

export interface QsMethodResult {
  chosen: string | null;
  written: number;
  removed: number;
  kept: string[];
  not_settable: string[];
}
