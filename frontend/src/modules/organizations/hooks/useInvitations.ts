import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { organizationsApi } from "../api/organizations.api";
import type {InvitationAcceptRequest, InvitationCreateRequest,
} from "../types/organization.types";
 
export const invitationKeys = {
  all: ["organizations", "invitations"] as const,
 
  list: (skip: number, limit: number) =>
    [...invitationKeys.all, "list", skip, limit] as const,
};
 
export function useInvitations(skip = 0, limit = 100) {
  return useQuery({
    queryKey: invitationKeys.list(skip, limit),
 
    queryFn: () => organizationsApi.listInvitations(skip, limit),
  });
}
 
export function useCreateInvitation() {
  const queryClient = useQueryClient();
 
  return useMutation({
    mutationFn: (payload: InvitationCreateRequest) =>
      organizationsApi.createInvitation(payload),
 
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invitationKeys.all });
    },
  });
}
 
export function useRevokeInvitation() {
  const queryClient = useQueryClient();
 
  return useMutation({
    mutationFn: organizationsApi.revokeInvitation,
 
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invitationKeys.all });
    },
  });
}
 
export function useAcceptInvitation() {
  return useMutation({
    mutationFn: (payload: InvitationAcceptRequest) =>
      organizationsApi.acceptInvitation(payload),
  });
}