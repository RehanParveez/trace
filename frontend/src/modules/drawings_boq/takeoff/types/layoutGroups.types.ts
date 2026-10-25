export interface LayoutSource {
  sheet_id: string;
  page_no: number;
  caption: string | null;
  floor: string | null;
  advice: string | null;
  role: string | null;
  rooms: number;
  room_area_m2: number;
  wall_m: number;
  items: number;
  open: number;
  accepted: number;
  rejected: number;
  set_aside: boolean;
}

export interface LayoutGroup {
  key: string;
  kind: "SAME" | "NEAR";
  state: "DOUBLE" | "CHOSEN" | "NONE" | "NEAR";
  floor: string | null;
  rooms: number;
  room_area_m2: number;
  chosen_sheet_id: string | null;
  suggested_sheet_id: string | null;
  conflict: boolean;
  choosable: boolean;
  counted_twice_m2: number;
  sources: LayoutSource[];
}

export interface LayoutGroups {
  drawing_id: string;
  groups: LayoutGroup[];
  to_decide: number;
  repeated_room_area_m2: number;
}

export type LayoutChoiceBody = { use_suggested: true } | { choices: { key: string; sheet_id: string }[] };

export interface LayoutChoiceResult {
  chosen: { key: string; sheet_id: string; page_no: number; set_aside: number; restored: number }[];
  set_aside: number;
  restored: number;
  blocked: { key: string; code: string; message: string }[];
  layouts: LayoutGroups;
}
