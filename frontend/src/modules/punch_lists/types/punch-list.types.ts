export type PunchListStatus = "OPEN" | "CLOSED";
export type PunchListItemStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "WAIVED";
export type PunchListPhotoPurpose = "DEFECT" | "RESOLUTION";

export interface PunchListItemPhoto {
  id: string;
  site_photo_id: string;
  photo_purpose: PunchListPhotoPurpose;
}

export interface PunchListItem {
  id: string;
  location: string;
  description: string;
  assigned_to_user_id: string | null;
  assigned_to_subcontractor_id: string | null;
  status: PunchListItemStatus;
  due_date: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  photos: PunchListItemPhoto[];
}

export interface PunchList {
  id: string;
  project_id: string;
  title: string;
  inspection_date: string;
  status: PunchListStatus;
  notes: string | null;
  closed_at: string | null;
  created_at: string;
}

export interface PunchListDetail extends PunchList {
  items: PunchListItem[];
}

export interface ProjectPunchListSummary {
  project_id: string;
  open_lists_count: number;
  total_open_items: number;
  is_project_clear: boolean;
}