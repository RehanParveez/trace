import { useQuery } from "@tanstack/react-query";
import { identityApi } from "../api/identity.api";

export function useInvitationPreview(token: string | null) {
  return useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => identityApi.previewInvitation(token!),
    enabled: Boolean(token),
    retry: false,
  });
}