export interface WallItem {
  item: string;
  share: number | null;
  quantity: number | null;
  unit: string | null;
}

export type FloorCompare = "COVERED" | "ONLY_THIS_FLOOR" | "NO_COMMON_FRAME" | null;

export interface WallRun {
  id: string;
  no: number;
  floor: string | null;
  page_no: number;
  name: string;
  faces: string[];
  thickness_mm: number;
  thickness_basis: string;
  construction: string;
  length_m: number;
  height_mm: number | null;
  height_basis: string | null;
  items: WallItem[];
  vs_below: FloorCompare;
  vs_above: FloorCompare;
  tol_mm: number;
}

export interface WallFloor {
  floor: string;
  runs: number;
  length_m: number;
  by_thickness_mm: Record<string, number>;
  only_vs_below: number;
  only_vs_above: number;
}

export interface WallSchedule {
  drawing_id: string;
  rows: WallRun[];
  floors: WallFloor[];
}
