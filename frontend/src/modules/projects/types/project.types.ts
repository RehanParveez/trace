export type ProjectStatus =
  | "PLANNING"
  | "ACTIVE"
  | "ON_HOLD"
  | "COMPLETED"
  | "CANCELLED";

export type ProjectMemberRole =
  | "MANAGER"
  | "ENGINEER"
  | "SUPERVISOR"
  | "SITE_MANAGER"
  | "MEMBER";

export interface Client {
  id: string;
  organization_id: string;
  name: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  notes: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface Project {
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
  created_at?: string;
  updated_at?: string;
}

export interface ProjectMemberUser {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: ProjectMemberRole;
  user?: ProjectMemberUser | null;
  created_at?: string;
  updated_at?: string;
}

export interface Milestone {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  due_date: string | null;
  completed_at: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ClientCreateRequest {
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
}

export interface ClientUpdateRequest {
  name?: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
}

export interface ProjectCreateRequest {
  name: string;
  code?: string | null;
  description?: string | null;
  client_id?: string | null;
  location?: string | null;
  status?: ProjectStatus;
  start_date?: string | null;
  expected_end_date?: string | null;
  actual_end_date?: string | null;
}

export interface ProjectUpdateRequest {
  name?: string;
  code?: string | null;
  description?: string | null;
  client_id?: string | null;
  location?: string | null;
  status?: ProjectStatus;
  start_date?: string | null;
  expected_end_date?: string | null;
  actual_end_date?: string | null;
}

export interface ProjectMemberCreateRequest {
  user_id: string;
  role: ProjectMemberRole;
}

export interface ProjectMemberUpdateRequest {
  role: ProjectMemberRole;
}

export interface MilestoneCreateRequest {
  name: string;
  description?: string | null;
  due_date?: string | null;
}

export interface MilestoneUpdateRequest {
  name?: string;
  description?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
}