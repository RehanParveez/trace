export type BillingInterval = "MONTHLY" | "YEARLY";

export type SubscriptionStatus =
  | "TRIALING"
  | "ACTIVE"
  | "PAST_DUE"
  | "CANCELLED"
  | "EXPIRED";

export type UsagePeriod = "MONTH" | "LIFETIME";

export interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price_monthly: number | string;
  price_yearly: number | string;
  currency: string;
  price_monthly_original?: number | string | null;
  price_yearly_original?: number | string | null;
  offer_label?: string | null;
  offer_ends_at?: string | null;
  version?: number;
  trial_days?: number;
  sort_order?: number;
  is_default?: boolean;
  limit_policy?: Record<string, "soft" | "hard">;
  is_active: boolean;
  is_public: boolean;
  features: Record<string, boolean>;
  quotas: Record<string, number | null>;
}
export interface Subscription {
  id: string;
  organization_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  billing_interval: BillingInterval;
  started_at: string;
  current_period_start: string;
  current_period_end: string;
  trial_ends_at: string | null;
  cancelled_at: string | null;
  cancel_at_period_end: boolean;
  provider: string;
}

export interface SubscriptionSummary {
  subscription: Subscription;
  plan: Plan;
}

export interface UsageMetric {
  metric: string;
  used: number;
  limit: number | null;
  remaining: number | null;
  percentage: number | null;
}

export interface UsageResponse {
  period_start: string;
  period_end: string;
  metrics: UsageMetric[];
}

export interface ChangePlanRequest {
  plan_id: string;
  billing_interval: BillingInterval;
  quantity?: number;
}

export interface CancelSubscriptionRequest {
  cancel_at_period_end: boolean;
  reason?: string | null;
  feedback?: string | null;
}

export interface SubscriptionListResponse {
  items: Subscription[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminSubscriptionListParams {
  status?: SubscriptionStatus;
  page?: number;
  page_size?: number;
}