import { useQuery } from "@tanstack/react-query";
import { aiRequestsApi } from "../api/ai-requests.api";
import type { AIRequestListParams } from "../types/ai-requests.types";

export const aiRequestKeys = {
  all: ["ai-requests"] as const,
  list: (params: AIRequestListParams) => [...aiRequestKeys.all, "list", params] as const,
  usageSummary: () => [...aiRequestKeys.all, "usage-summary"] as const,
};

export function useAIRequestLog(params: AIRequestListParams = {}) {
  return useQuery({
    queryKey: aiRequestKeys.list(params),
    queryFn: () => aiRequestsApi.listRequests(params),
  });
}

export function useAIUsageSummary() {
  return useQuery({
    queryKey: aiRequestKeys.usageSummary(),
    queryFn: aiRequestsApi.getUsageSummary,
  });
}