export interface BbsSheetRead {
  name: string;
  first_page: number;
  last_page: number;
  rows: number;
  printed_total_kg: string | null;
  computed_kg: string;
  diff_kg: string | null;
  reconciled: boolean;
}

export interface BbsUnreadLine {
  page: number;
  y: number;
  text: string;
  reason: string;
}

export interface BbsDroppedRepeat {
  page: number;
  sheet: number;
  sr: number | null;
  member: string | null;
}

export interface BbsRead {
  profile: string;
  pages: number;
  row_count: number;
  sheet_count: number;
  printed_total_kg: string;
  rows_total_kg: string;
  all_reconciled: boolean;
  sheets: BbsSheetRead[];
  dropped_repeats: BbsDroppedRepeat[];
  unread_count: number;
  unread_lines: BbsUnreadLine[];
}
