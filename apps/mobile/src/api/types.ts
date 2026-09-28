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