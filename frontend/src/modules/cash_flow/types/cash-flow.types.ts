export interface CashFlowSettings {
  procurement_payment_days: number; subcontractor_payment_days: number;
  client_collection_days: number; labour_lookback_days: number;
}

export interface CashFlowLineItem {
  event_date: string; category: "PROCUREMENT" | "LABOUR" | "SUBCONTRACTOR" | "CLIENT_COLLECTION";
  direction: "IN" | "OUT"; amount: number | string; description: string;
  is_estimated_timing: boolean; is_overdue: boolean;
}

export interface WeeklyBucket {
  week_start: string; week_end: string; total_inflow: number | string; total_outflow: number | string;
  net_change: number | string; cumulative_net: number | string; projected_balance: number | string | null;
}

export interface HorizonSummary { days: number; cumulative_net: number | string; projected_balance: number | string | null; }

export interface CashFlowForecast {
  as_of_date: string; horizon_days: number; currency: string; starting_cash_balance: number | string | null;
  weekly_buckets: WeeklyBucket[]; summaries: Record<number, HorizonSummary>;
  line_items: CashFlowLineItem[]; assumptions: CashFlowSettings;
  labour_daily_run_rate: number | string; limitations: string[];
}