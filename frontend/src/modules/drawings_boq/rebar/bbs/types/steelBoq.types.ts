export type SteelBoqState = "ADDED" | "REPLACED" | "UNCHANGED" | "CLEARED" | "NOTHING";

export interface SteelBoq {
  version_id: string;
  item_id: string;
  item_name: string;
  unit: string;
  source: string | null;
  effect_kg: string;
  delta: string;
  state: SteelBoqState;
  in_sync: boolean;
  quantity_now: string;
  quantity_after: string;
  net_quantity: string | null;
  adjustment_id: string | null;
  revoked: number;
  applied_count: number;
  open_count: number;
  note: string;
  dry_run: boolean;
}
