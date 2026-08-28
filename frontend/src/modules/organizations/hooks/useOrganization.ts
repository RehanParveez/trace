import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { organizationsApi } from "../api/organizations.api";
import type {AISettingsUpdateRequest, OrganizationUpdateRequest,
} from "../types/organization.types";
 
export const organizationKeys = {
  all: ["organizations"] as const,
 
  current: () => [...organizationKeys.all, "current"] as const,
 
  aiSettings: () => [...organizationKeys.all, "ai-settings"] as const,
};
 
export function useOrganization() {
  return useQuery({
    queryKey: organizationKeys.current(),
    queryFn: organizationsApi.getOrganization,
  });
}
 
export function useUpdateOrganization() {
  const queryClient = useQueryClient();
 
  return useMutation({
    mutationFn: (payload: OrganizationUpdateRequest) =>
      organizationsApi.updateOrganization(payload),
 
    onSuccess: (organization) => {
      queryClient.setQueryData(organizationKeys.current(), organization);
    },
  });
}
 
export function useAISettings() {
  return useQuery({
    queryKey: organizationKeys.aiSettings(),
    queryFn: organizationsApi.getAISettings,
  });
}
 
export function useUpdateAISettings() {
  const queryClient = useQueryClient();
 
  return useMutation({
    mutationFn: (payload: AISettingsUpdateRequest) =>
      organizationsApi.updateAISettings(payload),
 
    onSuccess: (settings) => {
      queryClient.setQueryData(organizationKeys.aiSettings(), settings);
 
      queryClient.setQueryData(organizationKeys.current(), (current) =>
        current
          ? {
              ...current,
              ai_enabled: settings.ai_enabled,
            }
          : current,
      );
    },
  });
}
 