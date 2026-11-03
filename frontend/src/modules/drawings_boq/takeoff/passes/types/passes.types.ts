export type TankKind = "OHWT" | "UGWT" | "SEPTIC";

export interface TankSource {
  route: string;
  page_no: number | null;
  text: string;
  key?: string | null;
}

export interface TankRecord {
  kind: TankKind;
  pages: number[];
  plan_mm: [number, number];
  depth_mm: number;
  wall_mm: number;
  top_mm: number;
  base_mm: number;
  sources: { plan: TankSource; depth: TankSource; wall: TankSource; top: TankSource; bottom: TankSource };
  complete: boolean;
  defaulted: boolean;
}

export type ElectricalReason = "NOT_COUNTABLE" | "TAG_NOT_ON_PLAN" | "NO_PLAN_HIT";

export interface ElectricalRow {
  index: number;
  name: string;
  description: string;
  kind: string;
  group: string;
  objects: number;
  token: string | null;
  counted_by: string | null;
  legend_page: number | null;
  plan_counts: Record<string, number>;
  total: number;
  set_aside_other_size: number;
  reason: ElectricalReason | null;
  work_item: string;
}

export interface ElectricalCoverage {
  pages: number[];
  floors: Record<string, string | null>;
  rows: ElectricalRow[];
  legend_symbols: number;
  counted: number;
  reasons: Record<string, number>;
}

export interface WallSteelStats {
  walls: number;
  attached: number;
  sections: number;
  problem: string | null;
}

export interface DrawingPasses {
  drawing_id: string;
  ran: boolean;
  tanks: TankRecord[];
  electrical: ElectricalCoverage | null;
  wall_steel: WallSteelStats | null;
  typed: Partial<Record<TankKind, string>>;
}

export interface TankSizeBody {
  kind: TankKind;
  value: string | null;
}
