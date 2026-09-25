export type ChangeOrderType = "ADDITION" | "OMISSION" | "VARIATION";
export type ChangeOrderStatus = "DRAFT" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface ChangeOrderLineItem {
  id: string;
  description: string;
  unit: string;
  boq_item_id: string | null;
  quantity: number | string;
  unit_rate: number | string | null;
  realized_value_impact: number | string | null;
  created_boq_item_id: string | null;
}

export interface ChangeOrder {
  id: string;
  project_id: string;
  boq_version_id: string;
  change_order_number: number;
  change_type: ChangeOrderType;
  status: ChangeOrderStatus;
  title: string;
  description: string | null;
  client_reference: string | null;
  value_impact: number | string;
  currency: string;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  version: number;
  created_at: string;
}

export interface ChangeOrderDetail extends ChangeOrder {
  line_items: ChangeOrderLineItem[];
}

export interface ProjectChangeOrderSummary {
  project_id: string;
  approved_count: number;
  approved_net_value_impact: number | string;
  draft_count: number;
  currency: string;
}