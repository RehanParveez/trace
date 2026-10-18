export interface ClosenessPoint {
  run_id: string;
  at: string;
  label: string;
  scope: string | null;
  closeness_pct: number | null;
  found_pct: number | null;
  adjusted_pct: number | null;
  within_tolerance: number | null;
  compared: number | null;
  open_differences: number | null;
  change: number | null;
}

export interface RangeDriverShare {
  name: string;
  basis: string;
  share_pct: number;
}

export interface RangeOpenShare {
  name: string;
  rows: number;
  quantity: number;
}

export interface RangeUnitPoint {
  unit: string;
  likely: number;
  spread_pct: number | null;
  change: number | null;
  open_rows: number;
  open_change: number | null;
  top_driver: RangeDriverShare | null;
  open_inputs: RangeOpenShare[];
}

export interface RangePoint {
  run_id: string;
  at: string;
  units: RangeUnitPoint[];
}

export interface RunHistory {
  project_id: string;
  current_run_id: string;
  closeness: ClosenessPoint[];
  ranges: RangePoint[];
}
