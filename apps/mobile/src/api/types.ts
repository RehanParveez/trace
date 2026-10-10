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

export type InvitationPreview = {
  organization_name: string;
  email: string;
  role_name: string;
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
  ingestion_meta: Record<string, unknown>;
  latest_audit_id: string | null;
};

export type BOQLifecycle =
  | "DRAFT"
  | "CALCULATING"
  | "CALCULATED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "ISSUED"
  | "SUPERSEDED"
  | "ARCHIVED";

export type BOQOrigin = "LEGACY" | "MANUAL" | "ENGINE";

export type BOQVersion = {
  id: string;
  project_id: string;
  drawing_id: string | null;
  label: string;
  status: "ACTIVE" | "SUPERSEDED";
  covered_area_sqft: number | string | null;
  export_meta: Record<string, unknown>;
  created_at: string;
  lifecycle: BOQLifecycle;
  origin: BOQOrigin;
  calculation_run_id: string | null;
  snapshot_id: string | null;
  rule_set_id: string | null;
  audit_score: number | string | null;
  approved_at: string | null;
  issued_at: string | null;
  priced_at: string | null;
  pricing_meta: Record<string, unknown>;
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
  work_item_code: string | null;
  description: string | null;
  net_quantity: number | string | null;
  adjustment_total: number | string;
  gross_quantity: number | string | null;
  waste_factor_applied: number | string | null;
  confidence: number | string | null;
  review_status: "OK" | "REVIEW_REQUIRED" | "WAIVED";
  source_kind: "LEGACY" | "MODEL" | "SCHEDULE_IMPORT" | "MANUAL" | "ESTIMATE";
  is_manual: boolean;
  canonical_unit: string | null;
  unit_factor: number | string | null;
  level_id: string | null;
  item_key: string | null;
  calculation_run_id: string | null;
  rate_book_id: string | null;
  base_rate: number | string | null;
  escalation_factor: number | string | null;
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

export type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
  new_password_confirmation: string;
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
  adjustment_reason?: string;
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

export type PhotoTagSource = "MANUAL" | "AI";

export type PhotoTag = {
  id: string;
  tag: string;
  confidence: number | null;
  source: PhotoTagSource;
};

export type SitePhoto = {
  id: string;
  project_id: string | null;
  storage_key: string;
  photo_url: string;
  sender_phone_number: string | null;
  caption_raw: string | null;
  caption_parsed: Record<string, unknown>;
  location_text: string | null;
  photo_date: string | null;
  is_ai_tagged: boolean;
  tags: PhotoTag[];
  created_at: string;
};

export type SitePhotoUpdatePayload = {
  location_text?: string | null;
  photo_date?: string | null; 
};

export type SitePhotoAssignProjectPayload = {
  project_id: string;
};

export type PhotoTagCreatePayload = {
  tag: string;
};

export type ProjectPhotoThumbnail = {
  project_id: string;
  photo_url: string;
};

export type WhatsAppChannel = {
  id: string;
  phone_number_id: string;
  business_account_id: string;
  display_phone_number: string | null;
  is_active: boolean;
  created_at: string;
};

export type ChannelConnectPayload = {
  phone_number_id: string;
  business_account_id: string;
  access_token: string;
  display_phone_number?: string | null;
};

export type ListSitePhotosFilters = {
  project_id?: string;
  tag?: string;
  photo_date_from?: string; 
  photo_date_to?: string;
  unassigned_only?: boolean;
  skip?: number;
  limit?: number; 
};

export type Subcontractor = {
  id: string;
  name: string;
  trade_specialization: string;
  contact_name: string | null;
  contact_phone: string | null;
  ntn_or_cnic: string | null;
  is_active_taxpayer: boolean;
  is_active: boolean;
  notes: string | null;
};

export type SubcontractorCreatePayload = {
  name: string;
  trade_specialization: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  ntn_or_cnic?: string | null;
  is_active_taxpayer: boolean;
  notes?: string | null;
};

export type SubcontractorUpdatePayload = {
  name?: string;
  trade_specialization?: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  ntn_or_cnic?: string | null;
  is_active_taxpayer: boolean;
  is_active?: boolean;
  notes?: string | null;
};

export type SubcontractAgreementStatus =
  | "ACTIVE"
  | "COMPLETED"
  | "TERMINATED";

export type SubcontractorBillStatus =
  | "DRAFT"
  | "ISSUED"
  | "CANCELLED";

export type AgreementItem = {
  id: string;
  description: string;
  unit: string;
  quantity: number | string;
  rate: number | string;
};

export type AgreementItemInput = {
  description: string;
  unit: string;
  quantity: number;
  rate: number;
};

export type SubcontractAgreement = {
  id: string;
  project_id: string;
  subcontractor_id: string;
  scope_description: string;
  contract_value: number | string;
  default_retention_percentage: number | string;
  default_retention_cap_percentage: number | string | null;
  start_date: string;
  end_date: string | null;
  status: SubcontractAgreementStatus;
  notes: string | null;
  version: number;
};

export type SubcontractAgreementDetail = SubcontractAgreement & {
  items: AgreementItem[];
};

export type SubcontractAgreementCreatePayload = {
  project_id: string;
  subcontractor_id: string;
  scope_description: string;
  start_date: string;
  default_retention_percentage: number;
  default_retention_cap_percentage?: number | null;
  notes?: string | null;
  items?: AgreementItemInput[] | null;
  contract_value?: number | null;
};

export type SubcontractAgreementUpdatePayload = {
  version: number;
  end_date?: string | null;
  status?: SubcontractAgreementStatus;
  default_retention_percentage?: number;
};

export type SubcontractorBillLineItem = {
  id: string;
  agreement_item_id: string;
  description: string;
  unit: string;
  contract_quantity: number | string;
  rate: number | string;
  previous_percentage: number | string;
  cumulative_percentage: number | string;
  this_period_value: number | string;
  cumulative_value: number | string;
};

export type SubcontractorBill = {
  id: string;
  project_id: string;
  agreement_id: string;
  bill_number: number;
  status: SubcontractorBillStatus;
  period_start: string;
  period_end: string;
  gross_value_this_period: number | string;
  gross_value_cumulative: number | string;
  retention_percentage: number | string;
  retention_cap_percentage: number | string | null;
  retention_this_period: number | string;
  retention_cumulative: number | string;
  other_deductions_amount: number | string;
  other_deductions_note: string | null;
  net_payable: number | string;
  retention_secured_by_guarantee: boolean;
  sales_tax_authority: string | null;
  sales_tax_rate_percentage: number | string | null;
  sales_tax_amount: number | string;
  total_amount_due: number | string;
  currency: string;
  notes: string | null;
  version: number;
  issued_at: string | null;
  created_at: string;
};

export type SubcontractorBillDetail = SubcontractorBill & {
  line_items: SubcontractorBillLineItem[];
};

export type SubcontractorBillCreatePayload = {
  period_start: string;
  period_end: string;
  retention_percentage?: number | null;
  retention_cap_percentage?: number | null;
  other_deductions_amount: number;
  other_deductions_note?: string | null;
  retention_secured_by_guarantee: boolean;
  sales_tax_authority?: "PRA" | "SRB" | "KPRA" | "BRA" | "ICT" | null;
  notes?: string | null;
  agreement_id: string;
  measurements: {
    agreement_item_id: string;
    cumulative_percentage: number;
  }[];
};

export type SubcontractorAdvance = {
  id: string;
  amount: number | string;
  advance_date: string;
  notes: string | null;
};

export type SubcontractorAdvanceCreatePayload = {
  amount: number;
  advance_date: string;
  notes?: string | null;
};

export type SubcontractorPayment = {
  id: string;
  bill_id: string | null;
  gross_amount: number | string;
  advance_recovered_amount: number | string;
  wht_category: string | null;
  wht_rate_percentage: number | string | null;
  wht_deducted_amount: number | string;
  net_paid_amount: number | string;
  payment_date: string;
  notes: string | null;
};

export type SubcontractorPaymentCreatePayload = {
  bill_id?: string | null;
  gross_amount: number;
  advance_recovered_amount: number;
  wht_category?:
    | "GOODS_SUPPLY"
    | "SERVICES"
    | "CONTRACTS_EXECUTION"
    | null;
  payment_date: string;
  notes?: string | null;
};

export type SubcontractorLedger = {
  agreement_id: string;
  contract_value: number | string;
  total_billed: number | string;
  total_paid: number | string;
  outstanding_bill_balance: number | string;
  total_advances_given: number | string;
  outstanding_advance_balance: number | string;
  currency: string;
};

export type ProjectSubcontractCost = {
  project_id: string;
  total_billed: number | string;
  currency: string;
};

export type LabourSourceType = "DIRECT" | "CONTRACTOR";
export type LabourDeploymentStatus = "ACTIVE" | "ENDED";
export type LabourWhtCategory =
  | "GOODS_SUPPLY"
  | "SERVICES"
  | "CONTRACTS_EXECUTION";

export type LabourSource = {
  id: string;
  name: string;
  source_type: LabourSourceType;
  contact_name: string | null;
  contact_phone: string | null;
  is_active_taxpayer: boolean;
  is_active: boolean;
  notes: string | null;
};

export type LabourSourceCreatePayload = {
  name: string;
  source_type: LabourSourceType;
  contact_name?: string | null;
  contact_phone?: string | null;
  is_active_taxpayer?: boolean;
  notes?: string | null;
};

export type LabourSourceUpdatePayload = {
  name?: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  is_active_taxpayer?: boolean;
  is_active?: boolean;
  notes?: string | null;
};

export type LabourWorker = {
  id: string;
  source_id: string;
  name: string;
  trade: string;
  cnic: string | null;
  phone: string | null;
  default_daily_rate: number | string | null;
  is_active: boolean;
};

export type LabourWorkerCreatePayload = {
  source_id: string;
  name: string;
  trade: string;
  cnic?: string | null;
  phone?: string | null;
  default_daily_rate?: number | null;
};

export type LabourWorkerUpdatePayload = {
  name?: string;
  trade?: string;
  cnic?: string | null;
  phone?: string | null;
  default_daily_rate?: number | null;
  is_active?: boolean;
};

export type LabourDeployment = {
  id: string;
  project_id: string;
  source_id: string;
  worker_id: string | null;
  trade: string;
  daily_rate: number | string;
  start_date: string;
  end_date: string | null;
  status: LabourDeploymentStatus;
};

export type LabourDeploymentCreatePayload = {
  source_id: string;
  worker_id?: string | null;
  trade: string;
  daily_rate: number;
  start_date: string;
};

export type LabourDeploymentUpdatePayload = {
  end_date?: string;
  status?: LabourDeploymentStatus;
};

export type LabourAttendance = {
  id: string;
  deployment_id: string;
  attendance_date: string;
  units_present: number | string;
  notes: string | null;
};

export type LabourAttendanceEntry = {
  deployment_id: string;
  attendance_date: string;
  units_present: number;
  notes?: string | null;
};

export type LabourAttendanceBulkResult = {
  created: number;
  updated: number;
  items: LabourAttendance[];
};

export type LabourTradeValue = {
  trade: string;
  cost: number | string;
};

export type LabourDayAttendanceSummary = {
  attendance_date: string;
  total_present: number | string;
  by_trade: LabourTradeValue[];
};

export type LabourAdvance = {
  id: string;
  source_id: string;
  worker_id: string | null;
  amount: number | string;
  advance_date: string;
  notes: string | null;
};

export type LabourAdvanceCreatePayload = {
  source_id: string;
  worker_id?: string | null;
  amount: number;
  advance_date: string;
  notes?: string | null;
};

export type LabourPayment = {
  id: string;
  source_id: string;
  worker_id: string | null;
  period_start: string;
  period_end: string;
  gross_wage_amount: number | string;
  advance_recovered_amount: number | string;
  wht_category: string | null;
  wht_rate_percentage: number | string | null;
  wht_deducted_amount: number | string;
  net_paid_amount: number | string;
  payment_date: string;
  notes: string | null;
};

export type LabourPaymentCreatePayload = {
  source_id: string;
  worker_id?: string | null;
  period_start: string;
  period_end: string;
  gross_wage_amount: number;
  advance_recovered_amount?: number;
  wht_category?: LabourWhtCategory | null;
  payment_date: string;
  notes?: string | null;
};

export type LabourCost = {
  period_start: string;
  period_end: string;
  total_cost: number | string;
  currency: string;
};

export type LabourBalance = {
  outstanding_advance_balance: number | string;
  currency: string;
};

export type LabourSummary = {
  project_id: string;
  period_start: string;
  period_end: string;
  total_accrued_cost: number | string;
  cost_by_trade: LabourTradeValue[];
  total_advances_given: number | string;
  total_payments_made: number | string;
  outstanding_advance_balance: number | string;
  currency: string;
};

export type BankGuaranteeHolderType = "CLIENT" | "SUBCONTRACTOR";
export type BankGuaranteePurpose = "RETENTION";
export type BankGuaranteeStatus = "ACTIVE" | "RENEWED" | "RELEASED" | "CALLED";

export type BankGuarantee = {
  id: string;
  project_id: string;
  holder_type: BankGuaranteeHolderType;
  boq_version_id: string | null;
  agreement_id: string | null;
  purpose: BankGuaranteePurpose;
  guarantee_number: string;
  issuing_bank: string;
  amount: number | string;
  currency: string;
  issue_date: string;
  expiry_date: string;
  status: BankGuaranteeStatus;
  renewed_from_guarantee_id: string | null;
  is_expired: boolean;
  is_expiring_soon: boolean;
  notes: string | null;
  created_at: string;
};

export type BankGuaranteeCreatePayload = {
  holder_type: BankGuaranteeHolderType;
  project_id: string;
  boq_version_id?: string | null;
  agreement_id?: string | null;
  guarantee_number: string;
  issuing_bank: string;
  amount: number;
  issue_date: string;
  expiry_date: string;
  notes?: string | null;
};

export type BankGuaranteeRenewPayload = {
  guarantee_number: string;
  issue_date: string;
  expiry_date: string;
  amount?: number;
  notes?: string | null;
};

export type ProjectBankGuaranteeSummary = {
  project_id: string;
  active_count: number;
  expiring_soon_count: number;
  expired_count: number;
  total_active_value: number | string;
  currency: string;
};

export type ChangeOrderType = "ADDITION" | "OMISSION" | "VARIATION";

export type ChangeOrderStatus =
  | "DRAFT"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED";

export type ChangeOrderLineItem = {
  id: string;
  description: string;
  unit: string;
  boq_item_id: string | null;
  quantity: number | string;
  unit_rate: number | string | null;
  realized_value_impact: number | string | null;
  created_boq_item_id: string | null;
};

export type ChangeOrder = {
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
};

export type ChangeOrderDetail = ChangeOrder & {
  line_items: ChangeOrderLineItem[];
};

export type ChangeOrderLineItemInput = {
  description: string;
  unit: string;
  boq_item_id?: string | null;
  quantity: number;
  unit_rate?: number | null;
};

export type ChangeOrderCreatePayload = {
  project_id: string;
  boq_version_id: string;
  change_type: ChangeOrderType;
  title: string;
  description?: string | null;
  client_reference?: string | null;
  line_items: ChangeOrderLineItemInput[];
};

export type ProjectChangeOrderSummary = {
  project_id: string;
  approved_count: number;
  approved_net_value_impact: number | string;
  draft_count: number;
  currency: string;
};

export type BudgetCategory = {
  id: string;
  name: string;
  allocated_amount: number | string;
};

export type Budget = {
  id: string;
  project_id: string;
  approved_amount: number | string;
  currency: string;
  notes: string | null;
  version: number;
  categories: BudgetCategory[];
  created_at: string;
  updated_at: string;
};

export type BudgetCategoryInput = {
  name: string;
  allocated_amount: number;
};

export type BudgetSavePayload = {
  project_id: string;
  approved_amount: number;
  currency?: string;
  notes?: string | null;
  categories?: BudgetCategoryInput[];
  version?: number | null;
};

export type BudgetOrganizationSummary = {
  total_approved_amount: number | string;
  budget_count: number;
  currency: string;
};

export type BudgetProjectSummary = {
  project_id: string;
  approved_amount: number | string;
  currency: string;
};

export type ExpenseStatus = "PENDING" | "APPROVED" | "REJECTED";

export type Expense = {
  id: string;
  project_id: string;
  category: string;
  description: string | null;
  amount: number | string;
  expense_date: string;
  status: ExpenseStatus;
  submitted_by: string | null;
  reviewed_by: string | null;
  review_note: string | null;
  created_at: string;
  updated_at: string;
};

export type ExpenseCreatePayload = {
  project_id: string;
  category: string;
  description?: string | null;
  amount: number;
  expense_date: string;
};

export type ExpenseReviewPayload = {
  note?: string | null;
};

export type ExpenseOrganizationSummary = {
  total_approved_amount: number | string;
  expense_count: number;
};

export type ExpenseStatusSummary = {
  totals: Partial<Record<ExpenseStatus, number | string>>;
};

export type ExpenseListParams = {
  project_id?: string;
  status?: ExpenseStatus;
  skip?: number;
  limit?: number;
};

export type AIRequestPurpose =
  | "MATERIAL_NORMALIZATION"
  | "CAPTION_PARSING"
  | "PHOTO_TAGGING"
  | "PDF_SCHEDULE_EXTRACTION";

export type AIEntityType =
  | "DRAWING_ELEMENT"
  | "SITE_PHOTO"
  | "WHATSAPP_MESSAGE"
  | "DRAWING";

export type AIProvider = "OLLAMA" | "ANTHROPIC";
export type AIResponseStatus = "SUCCEEDED" | "FAILED";

export type AIResponseSummary = {
  status: AIResponseStatus;
  parsed_output: Record<string, unknown> | null;
  error_message: string | null;
  latency_ms: number | null;
};

export type AIRequestRecord = {
  id: string;
  purpose: AIRequestPurpose;
  entity_type: AIEntityType | null;
  entity_id: string | null;
  provider: AIProvider;
  model: string;
  requested_by: string | null;
  created_at: string;
  response: AIResponseSummary | null;
};

export type AIUsageSummary = {
  total_requests: number;
  succeeded: number;
  failed: number;
  average_latency_ms: number | null;
};

export type NotificationType =
  | "DRAWING_PARSED"
  | "DRAWING_FAILED"
  | "BOQ_ITEM_APPROVED"
  | "SITE_PHOTO_NEEDS_PROJECT"
  | "PROGRESS_CLAIM_SUBMITTED"
  | "PROGRESS_CLAIM_APPROVED"
  | "PROGRESS_CLAIM_REJECTED"
  | "SUBSCRIPTION_USAGE_WARNING"
  | "MEMBER_JOINED"
  | "ORGANIZATION_INVITATION_RECEIVED";

export type AppNotification = {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  link_path: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export type NotificationUnreadCount = {
  unread_count: number;
};

export type AuditEntityType =
  | "ORGANIZATION"
  | "ROLE"
  | "MEMBER"
  | "INVITATION"
  | "SUBSCRIPTION"
  | "PROJECT"
  | "BOQ_ITEM"
  | "DRAWING"
  | "PROGRESS_CLAIM"
  | "WHATSAPP_CHANNEL"
  | "MATERIAL_LIBRARY"
  | "SITE_PHOTO"
  | "RUNNING_BILL"
  | "labour"
  | "subcontractor"
  | "retention"
  | "CHANGE_ORDER"
  | "SCHEDULE_TASK"
  | "PUNCH_LIST"
  | "BANK_GUARANTEE"
  | "BOQ_VERSION"
  | "REVIEW_ISSUE"
  | "BOQ_ADJUSTMENT";

export type AuditAction =
  | "CREATE"
  | "UPDATE"
  | "DELETE"
  | "APPROVE"
  | "REJECT"
  | "STATUS_CHANGE";

export type AuditLogEntry = {
  id: string;
  actor_user_id: string | null;
  actor_name: string | null;
  actor_email: string | null;
  entity_type: AuditEntityType;
  entity_id: string | null;
  action: AuditAction;
  summary: string;
  changes: Record<string, unknown>;
  created_at: string;
};

export type EntityActivitySummary = {
  entity_id: string;
  last_action: AuditAction;
  last_summary: string;
  last_created_at: string;
};

export type BOQVersionUpdatePayload = {
  covered_area_sqft?: number | null;
  export_meta?: Record<string, unknown>;
};

export type CalculationRunStatus =
  | "QUEUED"
  | "RUNNING"
  | "STAGED"
  | "PROMOTED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "SUPERSEDED";

export type CalculationRun = {
  id: string;
  project_id: string;
  rule_set_id: string;
  convention_code: string | null;
  drawing_revision_ids: string[];
  engine_version: string;
  fingerprint: string;
  status: CalculationRunStatus;
  progress_pct: number;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  stats: Record<string, unknown>;
  created_at: string;
  mode?: RunMode;
  baseline_run_id?: string | null;
  force_full?: boolean;
  verify?: boolean;
  attempts?: number;
};

export type RunStage = {
  stage: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "SKIPPED";
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  counts: Record<string, unknown>;
  error: string | null;
};

export type BOQBuildResult = {
  boq_version_id: string;
  items_created: number;
  items_updated: number;
  items_removed: number;
  orphaned_items: number;
  open_issues: number;
};

export type ReviewIssueStatus = "OPEN" | "RESOLVED" | "WAIVED";

export type ReviewIssue = {
  id: string;
  project_id: string;
  boq_version_id: string | null;
  boq_item_id: string | null;
  drawing_element_id: string | null;
  code: string;
  severity: "error" | "warning" | "info";
  blocks: "NONE" | "APPROVAL" | "ISSUE";
  message: string;
  suggested_fix: string | null;
  details: Record<string, unknown>;
  status: ReviewIssueStatus;
  resolution_note: string | null;
  resolved_at: string | null;
  created_at: string;
};

export type Adjustment = {
  id: string;
  boq_item_id: string;
  kind: "DELTA" | "REPLACE";
  value: number | string;
  reason: string;
  created_by_user_id: string | null;
  created_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
};

export type AdjustmentCreatePayload = {
  kind: "DELTA" | "REPLACE";
  value: number;
  reason: string;
};

export type Snapshot = {
  id: string;
  boq_version_id: string;
  version_no: number;
  purpose: "APPROVAL" | "ISSUE" | "MANUAL";
  content_hash: string;
  item_count: number;
  totals: Record<string, unknown>;
  rule_set_code: string | null;
  rule_set_version: number | null;
  convention_code: string | null;
  engine_version: string | null;
  note: string | null;
  created_at: string;
};

export type LedgerRow = {
  id: string;
  solid_id: string;
  element_id: string | null;
  level_id: string | null;
  work_item_code: string;
  quantity_net: number | string;
  unit: string;
  material_grade: string | null;
  source_kind: string;
  confidence: number | string;
  formula_code: string;
  trace: Record<string, unknown>;
  warnings: string[];
  engine_version: string;
};

export type Deduction = {
  id: string;
  from_solid_id: string;
  to_solid_id: string | null;
  deduction_type: string;
  quantity: number | string;
  unit: string;
  rule_code: string;
  rule_version: string | null;
  geometry: Record<string, unknown>;
  explanation: string | null;
  engine_version: string;
};

export type BarMark = {
  id: string;
  run_id: string;
  solid_id: string;
  mark: string;
  role: string;
  shape_code: string;
  designation: string | null;
  dia_mm: number | string;
  grade: string | null;
  count: number;
  spacing_mm: number | string | null;
  cut_len_mm: number | string;
  pieces: number;
  total_len_m: number | string;
  total_kg: number | string;
  provenance: string;
  confidence: number | string;
  review_status: string;
  warnings: string[];
};

export type ItemTrace = {
  item: BOQItem;
  ledger: LedgerRow[];
  deductions: Deduction[];
  adjustments: Adjustment[];
  bar_marks: BarMark[];
};

export type DrawingAudit = {
  id: string;
  drawing_id: string;
  overall_score: number | string;
  issues: Record<string, unknown>[];
  element_count: number;
  missing_material_count: number;
  zero_quantity_count: number;
  unclassified_proxy_count: number;
  extra_stats: Record<string, unknown>;
  created_at: string;
};

export type PriceVersionResult = {
  boq_version_id: string;
  as_of: string;
  rate_books: Record<string, unknown>[];
  priced: number;
  changed: number;
  unpriced: number;
  unit_mismatch: number;
  skipped_manual: number;
  skipped_other: number;
  by_source: Record<string, unknown>;
  total: string;
  open_issues: number;
};

export type ExportKind =
  |"CONTRACT_BOQ"
  |"PROCUREMENT"
  |"MEASUREMENT_BOOK"
  |"AUDIT_REPORT"
  |"REVISION_COMPARISON"
  |"BBS";

export type SnapshotItem = {
  id: string;
  line_no: number;
  source_item_id: string | null;
  work_item_code: string | null;
  material_name: string;
  description: string | null;
  item_type: string;
  unit: string;
  net_quantity: number | string | null;
  adjustment_total: number | string;
  quantity: number | string;
  gross_quantity: number | string | null;
  unit_rate: number | string | null;
  rate_source: string | null;
  base_rate: number | string | null;
  escalation_factor: number | string | null;
  amount: number | string | null;
  confidence: number | string | null;
  review_status: string;
  source_kind: string;
  ledger_row_count: number;
  ledger_hash: string | null;
};

export type DiffLine = {
  item_key: string;
  status: "ADDED" | "REMOVED" | "CHANGED" | "UNCHANGED" | string;
  work_item_code: string | null;
  material_name: string | null;
  unit_a: string | null;
  unit_b: string | null;
  unit_changed: boolean;
  net_a: number | string | null;
  net_b: number | string | null;
  quantity_a: number | string | null;
  quantity_b: number | string | null;
  rate_a: number | string | null;
  rate_b: number | string | null;
  amount_a: number | string | null;
  amount_b: number | string | null;
  net_delta: number | string | null;
  quantity_delta: number | string | null;
  quantity_delta_pct: number | string | null;
  rate_delta: number | string | null;
  amount_delta: number | string | null;
};

export type DiffSummary = {
  ADDED: number;
  REMOVED: number;
  CHANGED: number;
  UNCHANGED: number;
  total_a: number | string;
  total_b: number | string;
  total_delta: number | string;
  total_delta_pct: number | string | null;
  unpriced_a: number;
  unpriced_b: number;
};

export type DiffResult = {
  version_a_id: string;
  version_b_id: string;
  summary: DiffSummary;
  lines: DiffLine[];
};

export type DrawingElement = {
  id: string;
  ifc_global_id: string | null;
  ifc_type: string;
  name: string | null;
  raw_material_text: string | null;
  unit: string | null;
  quantity: number | string;
  discipline: string | null;
  structural_role: string | null;
  level_id: string | null;
  length_mm: number | string | null;
  width_mm: number | string | null;
  height_mm: number | string | null;
  thickness_mm: number | string | null;
  area_mm2: number | string | null;
  volume_mm3: number | string | null;
  normalization_status: string;
};

export type ScheduleKind = "DOOR" | "WINDOW" | "FINISH" | "FIXTURE" | "GENERAL";

export type ReviewDecision = "PENDING" | "CONFIRMED" | "REJECTED";

export type ScheduleImport = {
  id: string;
  project_id: string;
  drawing_id: string | null;
  source: string;
  schedule_kind: string;
  status: "PENDING_REVIEW" | "CONFIRMED" | "REJECTED" | "ARCHIVED" | string;
  file_name: string | null;
  row_count: number;
  confirmed_count: number;
  notes: string | null;
  extraction_meta: Record<string, unknown>;
  created_at: string;
  confirmed_at: string | null;
};

export type ScheduleRow = {
  id: string;
  schedule_import_id: string;
  row_no: number;
  schedule_kind: string;
  page_no: number | null;
  raw_text: string | null;
  mark: string | null;
  description: string | null;
  location_text: string | null;
  unit: string | null;
  quantity: number | string | null;
  width_mm: number | string | null;
  height_mm: number | string | null;
  work_item_code: string | null;
  canonical_unit: string | null;
  canonical_quantity: number | string | null;
  confidence: number | string;
  review_status: ReviewDecision | string;
  review_note: string | null;
  matched_element_count: number;
  surface: string | null;
  finish_name: string | null;
  notes: string[];
  quantity_defaulted: boolean;
};

export type ScheduleImportDetail = ScheduleImport & {
  rows: ScheduleRow[];
  summary: Record<string, unknown>;
};

export type ScheduleRowPayload = {
  mark?: string;
  description?: string;
  location_text?: string;
  unit?: string;
  quantity?: number;
  work_item_code?: string;
  width_mm?: number;
  height_mm?: number;
  surface?: string;
  finish_name?: string;
};

export type ConfirmImportResult = {
  schedule_import: ScheduleImport;
  finishes_created: number;
  finishes_updated: number;
  finish_conflicts: Record<string, unknown>[];
  ledger_lines: number;
  model_matched_rows: number;
  unlinked_finish_rows: number;
  count_mismatches: Record<string, unknown>[];
  rerun_recommended: boolean;
};

export type RebarRow = {
  id: string;
  schedule_import_id: string;
  row_no: number;
  page_no: number | null;
  raw_text: string | null;
  member_mark: string | null;
  mark: string | null;
  role: string | null;
  shape_code: string | null;
  designation: string | null;
  dia_mm: number | string | null;
  grade: string | null;
  count: number | null;
  spacing_mm: number | string | null;
  cut_len_mm: number | string | null;
  declared_total_kg: number | string | null;
  matched_element_id: string | null;
  confidence: number | string;
  review_status: ReviewDecision | string;
  review_note: string | null;
};

export type RebarRowPayload = {
  mark?: string;
  designation?: string;
  dia_mm?: number;
  count?: number;
  spacing_mm?: number;
  cut_len_mm?: number;
};

export type RebarImportDetail = {
  schedule_import_id: string;
  row_count: number;
  matched_count: number;
  unmatched_count: number;
  rows: RebarRow[];
};

export type RebarConfirmResult = {
  schedule_import_id: string;
  confirmed_count: number;
  rejected_count: number;
  pending_count: number;
};

export type RebarSummary = {
  boq_version_id: string;
  rows: {
    dia_mm: number | string;
    designation: string | null;
    grade: string | null;
    total_len_m: number | string;
    total_kg: number | string;
    mark_count: number;
  }[];
  total_kg: number | string;
  tier1_kg: number | string;
  tier2_kg: number | string;
  tier3_estimate_kg: number | string;
  bbs_exportable: boolean;
};

export type Surface = "FLOOR" | "WALL" | "CEILING" | "SKIRTING" | "DADO";

export type BuildingLevel = {
  id: string;
  name: string;
  elevation_mm: number | string | null;
  ifc_storey_id: string | null;
  sequence: number;
};

export type WorkItem = {
  id: string;
  code: string;
  description: string;
  unit: string;
  trade: string | null;
  is_active: boolean;
};

export type Space = {
  id: string;
  project_id: string;
  drawing_id: string | null;
  level_id: string | null;
  source: string;
  number: string | null;
  name: string | null;
  long_name: string | null;
  category: string;
  usage_text: string | null;
  is_external: boolean;
  is_active: boolean;
  gross_floor_area_mm2: number | string | null;
  net_floor_area_mm2: number | string | null;
  perimeter_mm: number | string | null;
  height_mm: number | string | null;
  geometry_kind: string;
  normalization_status: string;
  normalization_issues: { code?: string; severity?: string; message?: string }[];
  finish_count: number;
  boundary_count: number;
};

export type SpaceFinish = {
  id: string;
  space_id: string;
  surface: Surface | string;
  work_item_code: string;
  finish_name: string | null;
  height_mm: number | string | null;
  source: string;
  schedule_row_id: string | null;
  confidence: number | string;
  review_status: string;
  is_active: boolean;
};

export type SpaceBoundary = {
  element_id: string;
  name: string | null;
  ifc_type: string;
  structural_role: string | null;
  boundary_kind: string;
  side: string;
  source: string;
};

export type SpaceDetail = Space & {
  boundaries: SpaceBoundary[];
  finishes: SpaceFinish[];
};

export type SpacePayload = {
  number?: string;
  name?: string;
  long_name?: string;
  usage_text?: string;
  category?: string;
  level_id?: string;
  is_external?: boolean;
  is_active?: boolean;
  floor_area_m2?: number;
  perimeter_m?: number;
  height_m?: number;
};

export type SpaceFinishPayload = {
  surface: Surface;
  work_item_code: string;
  finish_name?: string;
  height_mm?: number;
};

export type FinishPreviewLine = {
  surface: string;
  work_item_code: string;
  unit: string;
  quantity: number | string;
  confidence: number | string;
  formula_code: string;
  source_kind: string;
  warnings: string[];
  steps: Record<string, unknown>[];
};

export type FinishPreview = {
  space_id: string;
  rule_set_code: string;
  resolved: Record<string, unknown>[];
  lines: FinishPreviewLine[];
  skipped: Record<string, unknown>;
};

export type RateBookStatus = "DRAFT" | "ACTIVE" | "SUPERSEDED" | "ARCHIVED";

export type RateBook = {
  id: string;
  organization_id: string | null;
  code: string;
  name: string;
  description: string | null;
  edition: string | null;
  currency: string;
  jurisdiction: string | null;
  province: string | null;
  city: string | null;
  effective_from: string | null;
  effective_to: string | null;
  status: RateBookStatus | string;
  immutable_version: number;
  published_at: string | null;
  content_hash: string | null;
  parent_rate_book_id: string | null;
  supersedes_rate_book_id: string | null;
  is_system: boolean;
  item_count: number;
  analysis_count: number;
  escalation_count: number;
};

export type RateBookPayload = {
  code?: string;
  name?: string;
  description?: string;
  edition?: string;
  currency?: string;
  jurisdiction?: string;
  province?: string;
  city?: string;
  effective_from?: string;
  effective_to?: string;
};

export type RateItem = {
  id: string;
  rate_book_id: string;
  work_item_code: string;
  unit: string;
  rate: number | string;
  description: string | null;
  trade: string | null;
  specification: string | null;
  csr_ref: string | null;
  analysis_id: string | null;
  is_active: boolean;
};

export type RateItemPayload = {
  work_item_code?: string;
  unit?: string;
  rate?: number;
  description?: string;
  trade?: string;
  specification?: string;
  csr_ref?: string;
  is_active?: boolean;
};

export type RateImportResult = { created: number; updated: number; total: number };

export type RateEscalation = {
  id: string;
  rate_book_id: string;
  trade_scope: string;
  effective_from: string;
  factor: number | string;
  note: string | null;
};

export type RateEscalationPayload = {
  trade_scope: string;
  effective_from: string;
  factor: number;
  note?: string;
};

export type AnalysisComponent = {
  id: string;
  sequence: number;
  component_type: string;
  description: string;
  work_item_code: string | null;
  rate_source: string;
  ref_rate_item_id: string | null;
  unit: string;
  coefficient: number | string;
  unit_rate: number | string | null;
};

export type RateAnalysis = {
  id: string;
  rate_book_id: string;
  code: string;
  work_item_code: string;
  description: string;
  unit: string;
  basis_quantity: number | string;
  overhead_pct: number | string;
  profit_pct: number | string;
  computed_rate: number | string | null;
  computed_at: string | null;
  is_active: boolean;
  components: AnalysisComponent[];
};

export type AnalysisBreakdown = {
  analysis_id: string;
  lines: Record<string, unknown>[];
  cost_by_type: Record<string, unknown>;
  cost: string;
  overhead: string;
  profit: string;
  total: string;
  basis_quantity: string;
  rate: string;
  unit: string;
};

export type RateOverride = {
  id: string;
  project_id: string;
  work_item_code: string;
  unit: string;
  rate: number | string;
  reason: string;
  effective_from: string | null;
  effective_to: string | null;
  created_by_user_id: string | null;
  created_at: string | null;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  revoke_reason: string | null;
};

export type RateOverridePayload = {
  work_item_code: string;
  unit: string;
  rate: number;
  reason: string;
  effective_from?: string;
  effective_to?: string;
};

export type PricingSummary = {
  boq_version_id: string;
  priced_at: string | null;
  pricing_meta: Record<string, unknown>;
  item_count: number;
  unpriced_count: number;
  by_source: Record<string, number>;
  total: string;
};

export type RateExplain = {
  item_id: string;
  work_item_code: string | null;
  unit: string;
  current: Record<string, unknown> | null;
  current_source: string | null;
  current_unit_rate: number | string | null;
  would_resolve_to: Record<string, unknown> | null;
  attempts: Record<string, unknown>[];
  stack: Record<string, unknown>[];
};

export type PriceVersionOptions = {
  rateBookIds?: string[];
  asOf?: string;
  overwriteManual?: boolean;
};

export type MaterialEntry = {
  id: string;
  raw_text: string;
  normalized_name: string;
  category: string | null;
  default_unit: string | null;
  default_rate: number | string | null;
  work_item_code: string | null;
  effective_from: string | null;
};

export type LabourRateEntry = {
  id: string;
  trade: string;
  unit: string;
  rate: number | string;
  work_item_code: string | null;
  effective_from: string | null;
};

export type BarSize = {
  id: string;
  standard: string;
  designation: string;
  grade: string;
  nominal_dia_mm: number | string;
  unit_weight_kg_m: number | string;
  is_system: boolean;
  is_active: boolean;
};

export type RebarShape = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  standard: string | null;
  segments: unknown[];
  bend_spec: unknown[];
  bend_count: number;
  hook_ends: number;
  is_system: boolean;
  is_active: boolean;
};

export type AnalysisComponentType = "MATERIAL" | "LABOUR" | "PLANT" | "OTHER";
export type AnalysisComponentSource = "DIRECT" | "RATE_ITEM" | "LABOUR_RATE" | "MATERIAL_LIBRARY";

export type AnalysisComponentInput = {
  component_type: AnalysisComponentType;
  description: string;
  work_item_code?: string;
  rate_source: AnalysisComponentSource;
  ref_rate_item_id?: string;
  unit: string;
  coefficient: number;
  unit_rate?: number;
};

export type AnalysisCreatePayload = {
  code: string;
  work_item_code: string;
  description: string;
  unit: string;
  basis_quantity: number;
  overhead_pct: number;
  profit_pct: number;
  components: AnalysisComponentInput[];
};

export type AnalysisUpdatePayload = {
  description?: string;
  unit?: string;
  basis_quantity?: number;
  overhead_pct?: number;
  profit_pct?: number;
  components?: AnalysisComponentInput[];
};

export type BulkRateInput = {
  work_item_code: string;
  unit: string;
  rate: number;
  description?: string;
  trade?: string;
}

export type RuleSet = {
  id: string;
  organization_id: string | null;
  code: string;
  name: string;
  description: string | null;
  jurisdiction: string | null;
  province: string | null;
  city: string | null;
  standard_name: string | null;
  standard_edition: string | null;
  effective_from: string | null;
  effective_to: string | null;
  status: string;
  immutable_version: number;
  convention_code: string | null;
  is_system: boolean;
  published_at: string | null;
  content_hash: string | null;
  supersedes_rule_set_id: string | null;
  wall_measurement_method: string;
  net_vs_gross_preference: string;
  preferred_units: Record<string, unknown>;
  extra_config: Record<string, unknown>;
};

export type RuleRow = Record<string, unknown>;

export type RecipeComponent = {
  sequence: number;
  work_item_code: string | null;
  description_template: string;
  unit: string;
  quantity_formula_code: string;
  output_unit: string;
  category: string | null;
  item_type: string;
  is_optional: boolean;
};

export type Recipe = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  trigger_ifc_types: string[];
  trigger_conditions: Record<string, unknown>;
  is_active: boolean;
  components: RecipeComponent[];
};

export type RuleSetDetail = {
  rule_set: RuleSet;
  opening_rules: RuleRow[];
  wastage_rules: RuleRow[];
  reinforcement_rules: RuleRow[];
  mappings: RuleRow[];
  recipes: Recipe[];
  finish_rules: RuleRow[];
};

export type RuleSectionKey =
  | "opening_rules"
  | "wastage_rules"
  | "reinforcement_rules"
  | "mappings"
  | "finish_rules";

export type RuleValidationIssue = {
  code: string;
  severity: "error" | "warning" | "info";
  message: string;
  ref: string | null;
};

export type RuleValidation = { valid: boolean; issues: RuleValidationIssue[] };

export type RulePublishResult = { rule_set: RuleSet; warnings: RuleValidationIssue[] };

export type RecipePayload = {
  code: string;
  name: string;
  description?: string;
  trigger_ifc_types: string[];
  trigger_conditions: Record<string, unknown>;
  components: {
    sequence: number;
    work_item_code?: string;
    description_template: string;
    unit: string;
    quantity_formula_code: string;
    category?: string;
    item_type: "MATERIAL" | "LABOUR" | "CUSTOM";
    is_optional: boolean;
  }[];
};

export type Formula = {
  code: string;
  output_unit: string;
  description: string;
  input_unit: string | null;
  needs_kernel: boolean;
};

export type Convention = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  conserves_volume: boolean;
  parameters: Record<string, unknown>;
};

export type FinishOptions = {
  surfaces: { surface: string; unit: string; needs_height: boolean }[];
  categories: string[];
};

export type WorkItemFull = {
  id: string;
  organization_id: string | null;
  code: string;
  description: string;
  unit: string;
  trade: string | null;
  wbs_code: string | null;
  specification: string | null;
  csr_ref: string | null;
  default_formula_code: string | null;
  is_system: boolean;
  is_active: boolean;
  extra: Record<string, unknown>;
};

export type QuantitySolid = {
  id: string;
  element_id: string | null;
  level_id: string | null;
  role: string;
  component_type: string;
  geometry_kind: string;
  gross_volume_m3: number | string | null;
  gross_area_m2: number | string | null;
  gross_length_m: number | string | null;
  count: number | null;
  status: string;
  issues: { code?: string; severity?: string; message?: string }[];
};

export type ProjectBoqCount = {
  project_id: string;
  latest_boq_item_count: number;
};

export type CursorPage<T> = { rows: T[]; next: string | null };

export type RunMode = "FULL" | "INCREMENTAL";

export type StageTiming = {
  stage: string;
  status: string;
  duration_ms: number | null;
  peak_rss_mb: number | null;
};

export type RunBudget = {
  name: string;
  limit: number;
  actual: number | null;
  unit: string;
  ok: boolean | null;
};

export type RunAllocation = {
  mode?: RunMode;
  fallback_reason?: string;
  participating?: number;
  reused?: number;
  recompute?: number;
  changed?: number;
  added?: number;
  modified?: number;
  removed?: number;
  affected_by_neighbourhood?: number;
  order_flips?: number;
  remap_misses?: number;
  geometry_built?: number;
};

export type RunVerifyResult = {
  checked: boolean;
  matched: boolean;
  problems?: unknown[];
};

export type RunFailure = {
  code: string;
  stage: string | null;
  message: string;
};

export type RunMetrics = {
  run_id: string;
  project_id: string;
  status: string;
  mode: RunMode;
  baseline_run_id: string | null;
  engine_version: string;
  fingerprint: string;
  attempts: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  stages: StageTiming[];
  timings_ms: Record<string, number>;
  counts: Record<string, unknown>;
  allocation: RunAllocation;
  verify: RunVerifyResult | null;
  peak_rss_mb: number | null;
  failure: RunFailure | null;
  budgets: RunBudget[];
};

export type QuotaUsage = {
  used: number;
  limit: number | null;
  remaining: number | null;
  period_start?: string | null;
  period_end?: string | null;
};

export type ConcurrentUsage = { active: number; limit: number };

export type RateLimitWindow = {
  window_seconds: number;
  limit: number;
  used: number;
  remaining: number;
  resets_in_seconds: number;
};

export type CalcUsage = {
  quota: QuotaUsage | null;
  concurrent: ConcurrentUsage;
  rate_limits: RateLimitWindow[];
};

export type SlowRun = {
  run_id: string;
  project_id: string;
  mode: RunMode;
  duration_seconds: number;
  elements: number;
};

export type OrgCalcMetrics = {
  organization_id: string;
  window_days: number;
  runs_total: number;
  runs_by_status: Record<string, number>;
  runs_by_mode: Record<string, number>;
  failure_codes: Record<string, number>;
  active_now: number;
  duration_seconds: { p50: number | null; p95: number | null; max: number | null };
  elements_processed: number;
  warnings_total: number;
  incremental_share: number;
  slowest_runs: SlowRun[];
  usage: CalcUsage;
};

export type ImpactElement = {
  element_id: string;
  ifc_type: string | null;
  name: string | null;
  ifc_global_id: string | null;
  overlap_mm3: number | null;
};

export type ImpactLedgerRow = {
  element_id: string | null;
  work_item_code: string;
  quantity_net: string | number;
  unit: string;
  ledger_id: string;
};

export type ElementImpact = {
  run_id: string;
  element_id: string;
  touching: ImpactElement[];
  affected_ledger: ImpactLedgerRow[];
  truncated: boolean;
};