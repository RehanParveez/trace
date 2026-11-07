import { useQuery } from "@tanstack/react-query";
import { billingApi } from "../api/billing.api";

export const billingKeys = {
  all: ["drawings-boq", "billing"] as const,
  view: (projectId: string, profile: string) => ["drawings-boq", "billing", projectId, profile] as const,
};

export function useBilling(projectId: string | undefined, profile: string) {
  return useQuery({
    queryKey: billingKeys.view(projectId ?? "", profile),
    queryFn: () => billingApi.get(projectId as string, profile),
    enabled: Boolean(projectId),
  });
}
