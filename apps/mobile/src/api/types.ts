export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type AuthPermission = {
  id: string;
  key: string;
  description: string | null;
};

export type AuthRole = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: AuthPermission[];
};

export type AuthOrganization = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
};

export type AuthUser = {
  id: string;
  organization_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  role: AuthRole;
  organization: AuthOrganization;
  is_platform_admin: boolean;
};

export type LoginResponse = {
  user: AuthUser;
  tokens: AuthTokens;
};

export type CurrentUserResponse = {
  user: AuthUser;
};

export type ApiErrorBody = {
  detail?: string | Array<{ msg?: string }>;
  message?: string;
};

export type RegisterPayload = {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  password_confirmation: string;
  organization_name?: string;
  invitation_token?: string;
};

export type MessageResponse = {
  message: string;
};

export type RegistrationResponse = {
  user: AuthUser;
  verification_required: boolean;
  message: string;
};

export type ProjectStatus =
  | "PLANNING"
  | "ACTIVE"
  | "ON_HOLD"
  | "COMPLETED"
  | "CANCELLED";

export type Project = {
  id: string;
  organization_id: string;
  client_id: string | null;
  name: string;
  code: string | null;
  description: string | null;
  location: string | null;
  status: ProjectStatus;
  start_date: string | null;
  expected_end_date: string | null;
  actual_end_date: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectCreatePayload = {
  name: string;
  code?: string | null;
  description?: string | null;
  location?: string | null;
  client_id?: string | null;
  start_date?: string | null;
  expected_end_date?: string | null;
};

export type ProjectMemberRole =
  | "MANAGER"
  | "ENGINEER"
  | "SUPERVISOR"
  | "SITE_MANAGER"
  | "MEMBER";

export type ProjectMember = {
  id: string;
  project_id: string;
  user_id: string;
  role: ProjectMemberRole;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
  };
  created_at: string;
  updated_at: string;
};

export type OrganizationMember = {
  id: string;
  organization_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  role: AuthRole;
};

export type ProjectUpdatePayload = {
  name?: string;
  code?: string | null;
  description?: string | null;
  location?: string | null;
  client_id?: string | null;
  status?: ProjectStatus;
  start_date?: string | null;
  expected_end_date?: string | null;
  actual_end_date?: string | null;
};

export type ClientPayload = {
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
};

export type Milestone = {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MilestonePayload = {
  name: string;
  description?: string | null;
  due_date?: string | null;
};

export type MilestoneUpdatePayload = {
  name?: string;
  description?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
};

export type Client = {
  id: string;
  organization_id: string;
  name: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  notes: string | null;
};

export type Drawing = {
  id: string;
  project_id: string;
  original_filename: string;
  format: "IFC" | "PDF" | "DWG" | "DXF" | "RVT";
  status: "UPLOADED" | "PROCESSING" | "PARSED" | "FAILED";
  file_size_bytes: number;
  error_message: string | null;
  parsed_at: string | null;
  created_at: string;
  revision_group_id: string;
  revision_label: string | null;
  is_current_revision: boolean;
  superseded_at: string | null;
};

export type BOQVersion = {
  id: string;
  project_id: string;
  drawing_id: string | null;
  label: string;
  status: "ACTIVE" | "SUPERSEDED";
  covered_area_sqft: number | string | null;
  export_meta: Record<string, unknown>;
  created_at: string;
};

export type BOQItem = {
  id: string;
  boq_version_id: string;
  drawing_element_id: string | null;
  material_name: string;
  category: string | null;
  unit: string;
  quantity: number | string;
  unit_rate: number | string | null;
  rate_source: string | null;
  status: "DRAFT" | "APPROVED";
  version: number;
  approved_at: string | null;
  item_type: "MATERIAL" | "LABOUR" | "CUSTOM";
  created_by_user_id: string | null;
};

export type BOQSummary = {
  boq_version_id: string;
  materials_total: number | string;
  labour_total: number | string;
  custom_total: number | string;
  grand_total: number | string;
  cost_per_sqft: number | string | null;
  covered_area_sqft: number | string | null;
  amount_in_words: string;
  unpriced_item_count: number;
  unapproved_item_count: number;
  item_count: number;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  ai_enabled: boolean;
  currency: string;
  created_at: string;
  updated_at: string;
};

export type OrganizationUpdatePayload = {
  name?: string;
  slug?: string;
  ai_enabled?: boolean;
  currency?: string;
};

export type OrganizationRole = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: AuthPermission[];
};

export type OrganizationInvitation = {
  id: string;
  email: string;
  role_id: string;
  invited_by_user_id: string;
  accepted_by_user_id: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type RolePayload = {
  name: string;
  description?: string | null;
  permission_ids: string[];
};

export type InvitationAcceptance = {
  message: string;
  organization_id: string;
  organization_name: string;
  role_id: string;
  role_name: string;
};

export type BOQVersionCreatePayload = {
  label: string;
};

export type BOQCustomItemCreatePayload = {
  material_name: string;
  category?: string | null;
  unit: string;
  quantity: number;
  unit_rate?: number | null;
};

export type BOQItemUpdatePayload = {
  version: number;
  material_name?: string;
  category?: string | null;
  unit?: string;
  quantity?: number;
  unit_rate?: number | null;
  save_as_library_default?: boolean;
};

export type ProgressClaimStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "APPROVED"
  | "REJECTED";

export type ProgressClaim = {
  id: string;
  organization_id: string;
  project_id: string;
  boq_item_id: string;
  claim_date: string;
  claimed_quantity: number | string;
  claimed_percentage: number | string;
  notes: string | null;
  status: ProgressClaimStatus;
  submitted_by: string | null;
  submitted_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ProgressClaimCreatePayload = {
  project_id: string;
  boq_item_id: string;
  claim_date: string;
  claimed_quantity: number;
  claimed_percentage: number;
  notes?: string | null;
};

export type ProgressClaimUpdatePayload = {
  version: number;
  claim_date?: string;
  claimed_quantity?: number;
  claimed_percentage?: number;
  notes?: string | null;
};

export type ProgressClaimReviewPayload = {
  version: number;
  note?: string | null;
};

export type BillingInterval = "MONTHLY" | "YEARLY";

export type SubscriptionStatus =
  | "TRIALING"
  | "ACTIVE"
  | "PAST_DUE"
  | "CANCELLED"
  | "EXPIRED";

export type UsagePeriod = "MONTH" | "LIFETIME";

export type Plan = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price_monthly: string | number;
  price_yearly: string | number;
  currency: string;
  price_monthly_original: string | number | null;
  price_yearly_original: string | number | null;
  offer_label: string | null;
  offer_ends_at: string | null;
  version: number;
  trial_days: number;
  sort_order: number;
  is_default: boolean;
  is_active: boolean;
  is_public: boolean;
  features: Record<string, boolean | unknown>;
  quotas: Record<string, number | null>;
  limit_policy: Record<string, string>;
};

export type Subscription = {
  id: string;
  organization_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  billing_interval: BillingInterval;
  quantity: number;
  started_at: string;
  current_period_start: string;
  current_period_end: string;
  trial_ends_at: string | null;
  cancelled_at: string | null;
  cancel_at_period_end: boolean;
  grace_period_ends_at: string | null;
  cancellation_reason: string | null;
  last_payment_at: string | null;
  next_billing_at: string | null;
  provider: string;
};

export type SubscriptionSummary = {
  subscription: Subscription;
  plan: Plan;
};

export type UsageMetric = {
  metric: string;
  used: number;
  limit: number | null;
  remaining: number | null;
  percentage: number | null;
};

export type Usage = {
  period_start: string;
  period_end: string;
  metrics: UsageMetric[];
};

export type ChangePlanPayload = {
  plan_id: string;
  billing_interval: BillingInterval;
  quantity: number;
};

export type CancelSubscriptionPayload = {
  cancel_at_period_end: boolean;
  reason?: string | null;
  feedback?: string | null;
};

export interface SiteLog {
  id: string;
  project_id: string;
  log_date: string;              
  workforce_count: number | null;
  weather: string | null;
  blockers: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SiteLogCreatePayload {
  project_id: string;
  log_date: string;              
  workforce_count?: number | null;
  weather?: string | null;
  blockers?: string | null;
  notes?: string | null;
}

export interface SiteLogUpdatePayload {
  log_date?: string;
  workforce_count?: number | null;
  weather?: string | null;
  blockers?: string | null;
  notes?: string | null;
}