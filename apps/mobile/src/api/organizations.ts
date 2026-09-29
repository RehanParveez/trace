import { authenticatedRequest } from "./client";
import type {AuthPermission, InvitationAcceptance, Organization, OrganizationInvitation, OrganizationMember, OrganizationRole, OrganizationUpdatePayload, RolePayload,
} from "./types";

const body = (value: unknown) => JSON.stringify(value);

export const getOrganization = () =>
  authenticatedRequest<Organization>("/organizations/me");

export const updateOrganization = (payload: OrganizationUpdatePayload) =>
  authenticatedRequest<Organization>("/organizations/me", {
    method: "PATCH",
    body: body(payload),
  });

export const getAISettings = () =>
  authenticatedRequest<{ ai_enabled: boolean }>(
    "/organizations/me/ai-settings",
  );

export const updateAISettings = (ai_enabled: boolean) =>
  authenticatedRequest<{ ai_enabled: boolean }>(
    "/organizations/me/ai-settings",
    { method: "PATCH", body: body({ ai_enabled }) },
  );

export const listMembers = (skip = 0, limit = 100) =>
  authenticatedRequest<OrganizationMember[]>(
    `/organizations/me/members?skip=${skip}&limit=${limit}`,
  );

export const getMember = (userId: string) =>
  authenticatedRequest<OrganizationMember>(
    `/organizations/me/members/${userId}`,
  );

export const updateMemberRole = (userId: string, role_id: string) =>
  authenticatedRequest<OrganizationMember>(
    `/organizations/me/members/${userId}/role`,
    { method: "PATCH", body: body({ role_id }) },
  );

export const updateMemberStatus = (userId: string, is_active: boolean) =>
  authenticatedRequest<OrganizationMember>(
    `/organizations/me/members/${userId}/status`,
    { method: "PATCH", body: body({ is_active }) },
  );

export const listRoles = () =>
  authenticatedRequest<OrganizationRole[]>("/organizations/me/roles");

export const getRole = (roleId: string) =>
  authenticatedRequest<OrganizationRole>(
    `/organizations/me/roles/${roleId}`,
  );

export const createRole = (payload: RolePayload) =>
  authenticatedRequest<OrganizationRole>("/organizations/me/roles", {
    method: "POST",
    body: body(payload),
  });

export const updateRole = (
  roleId: string,
  payload: Partial<RolePayload>,
) =>
  authenticatedRequest<OrganizationRole>(
    `/organizations/me/roles/${roleId}`,
    { method: "PATCH", body: body(payload) },
  );

export const deleteRole = (roleId: string) =>
  authenticatedRequest<void>(`/organizations/me/roles/${roleId}`, {
    method: "DELETE",
  });

export const listPermissions = () =>
  authenticatedRequest<AuthPermission[]>("/organizations/me/permissions");

export const listInvitations = (skip = 0, limit = 100) =>
  authenticatedRequest<OrganizationInvitation[]>(
    `/organizations/me/invitations?skip=${skip}&limit=${limit}`,
  );

export const createInvitation = (email: string, role_id: string) =>
  authenticatedRequest<OrganizationInvitation>(
    "/organizations/me/invitations",
    {
      method: "POST",
      body: body({ email: email.trim().toLowerCase(), role_id }),
    },
  );

export const revokeInvitation = (invitationId: string) =>
  authenticatedRequest<void>(
    `/organizations/me/invitations/${invitationId}`,
    { method: "DELETE" },
  );

export const acceptInvitation = (token: string) =>
  authenticatedRequest<InvitationAcceptance>(
    "/organizations/invitations/accept",
    { method: "POST", body: body({ token: token.trim() }) },
  );