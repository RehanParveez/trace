import { apiClient } from "../../../shared/api/client";
import type {
  AISettingsResponse,
  AISettingsUpdateRequest,
  Invitation,
  InvitationAcceptanceResponse,
  InvitationAcceptRequest,
  InvitationCreateRequest,
  Member,
  MemberRoleUpdateRequest,
  MemberStatusUpdateRequest,
  Organization,
  OrganizationUpdateRequest,
  Permission,
  Role,
  RoleCreateRequest,
  RoleUpdateRequest,
} from "../types/organization.types";
 
export const organizationsApi = {
  async getOrganization(): Promise<Organization> {
    const response = await apiClient.get<Organization>("/organizations/me");
 
    return response.data;
  },
 
  async updateOrganization(
    payload: OrganizationUpdateRequest,
  ): Promise<Organization> {
    const response = await apiClient.patch<Organization>(
      "/organizations/me",
      payload,
    );
 
    return response.data;
  },
 
  async getAISettings(): Promise<AISettingsResponse> {
    const response = await apiClient.get<AISettingsResponse>(
      "/organizations/me/ai-settings",
    );
 
    return response.data;
  },
 
  async updateAISettings(
    payload: AISettingsUpdateRequest,
  ): Promise<AISettingsResponse> {
    const response = await apiClient.patch<AISettingsResponse>(
      "/organizations/me/ai-settings",
      payload,
    );
 
    return response.data;
  },
 
  async listMembers(skip = 0, limit = 100): Promise<Member[]> {
    const response = await apiClient.get<Member[]>(
      "/organizations/me/members",
      { params: { skip, limit } },
    );
 
    return response.data;
  },
 
  async getMember(userId: string): Promise<Member> {
    const response = await apiClient.get<Member>(
      `/organizations/me/members/${userId}`,
    );
 
    return response.data;
  },
 
  async updateMemberRole(
    userId: string,
    payload: MemberRoleUpdateRequest,
  ): Promise<Member> {
    const response = await apiClient.patch<Member>(
      `/organizations/me/members/${userId}/role`,
      payload,
    );
 
    return response.data;
  },
 
  async updateMemberStatus(
    userId: string,
    payload: MemberStatusUpdateRequest,
  ): Promise<Member> {
    const response = await apiClient.patch<Member>(
      `/organizations/me/members/${userId}/status`,
      payload,
    );
 
    return response.data;
  },
 
  async listRoles(): Promise<Role[]> {
    const response = await apiClient.get<Role[]>("/organizations/me/roles");
 
    return response.data;
  },
 
  async getRole(roleId: string): Promise<Role> {
    const response = await apiClient.get<Role>(
      `/organizations/me/roles/${roleId}`,
    );
 
    return response.data;
  },
 
  async createRole(payload: RoleCreateRequest): Promise<Role> {
    const response = await apiClient.post<Role>(
      "/organizations/me/roles",
      payload,
    );
 
    return response.data;
  },
 
  async updateRole(
    roleId: string,
    payload: RoleUpdateRequest,
  ): Promise<Role> {
    const response = await apiClient.patch<Role>(
      `/organizations/me/roles/${roleId}`,
      payload,
    );
 
    return response.data;
  },
 
  async deleteRole(roleId: string): Promise<void> {
    await apiClient.delete(`/organizations/me/roles/${roleId}`);
  },
 
  async listPermissions(): Promise<Permission[]> {
    const response = await apiClient.get<Permission[]>(
      "/organizations/me/permissions",
    );
 
    return response.data;
  },
 
  async createInvitation(
    payload: InvitationCreateRequest,
  ): Promise<Invitation> {
    const response = await apiClient.post<Invitation>(
      "/organizations/me/invitations",
      payload,
    );
 
    return response.data;
  },
 
  async listInvitations(skip = 0, limit = 100): Promise<Invitation[]> {
    const response = await apiClient.get<Invitation[]>(
      "/organizations/me/invitations",
      { params: { skip, limit } },
    );
 
    return response.data;
  },
 
  async revokeInvitation(invitationId: string): Promise<void> {
    await apiClient.delete(`/organizations/me/invitations/${invitationId}`);
  },
 
  async acceptInvitation(
    payload: InvitationAcceptRequest,
  ): Promise<InvitationAcceptanceResponse> {
    const response = await apiClient.post<InvitationAcceptanceResponse>(
      "/organizations/invitations/accept",
      payload,
    );
 
    return response.data;
  },
};