export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  ai_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrganizationUpdateRequest {
  name?: string;
  slug?: string;
  ai_enabled?: boolean;
}

export interface AISettingsResponse {
  ai_enabled: boolean;
}

export interface AISettingsUpdateRequest {
  ai_enabled: boolean;
}

export interface Permission {
  id: string;
  key: string;
  description: string | null;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
}

export interface RoleCreateRequest {
  name: string;
  description?: string | null;
  permission_ids: string[];
}

export interface RoleUpdateRequest {
  name?: string;
  description?: string | null;
  permission_ids?: string[];
}

export interface Member {
  id: string;
  organization_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  role: Role;
}

export interface MemberRoleUpdateRequest {
  role_id: string;
}

export interface MemberStatusUpdateRequest {
  is_active: boolean;
}

export interface InvitationCreateRequest {
  email: string;
  role_id: string;
}

export interface InvitationAcceptRequest {
  token: string;
}

export interface InvitationAcceptanceResponse {
  message: string;
  organization_id: string;
  organization_name: string;
  role_id: string;
  role_name: string;
}

export interface Invitation {
  id: string;
  email: string;
  role_id: string;
  invited_by_user_id: string;
  accepted_by_user_id: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
}

export type OrganizationPermissionKey =
  | "organization:read"
  | "organization:manage"
  | "organization:members_manage";

export type OrganizationIconName =
  | "building"
  | "settings"
  | "users"
  | "shield"
  | "mail"
  | "spark"
  | "check"
  | "x"
  | "arrow"
  | "chevron"
  | "edit"
  | "plus"
  | "search"
  | "more"
  | "user"
  | "lock"
  | "logout"
  | "dashboard"
  | "projects"
  | "budget"
  | "site"
  | "procurement"
  | "expenses"
  | "info"
  | "refresh";