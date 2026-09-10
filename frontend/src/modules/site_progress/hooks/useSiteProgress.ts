import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { siteProgressApi } from "../api/site-progress.api";
import type {SiteLogCreateRequest, SiteLogListParams, SiteLogUpdateRequest,
} from "../types/site-progress.types";

export const siteProgressKeys = {
  all: ["site-progress"] as const,
  list: (params: SiteLogListParams) => [...siteProgressKeys.all, "list", params] as const,
};

export function useSiteLogs(params: SiteLogListParams = {}) {
  return useQuery({
    queryKey: siteProgressKeys.list(params),
    queryFn: () => siteProgressApi.listLogs(params),
  });
}

function invalidateSiteLogLists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({
    queryKey: siteProgressKeys.all,
    predicate: (query) => query.queryKey[1] === "list",
  });
}

export function useCreateSiteLog() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SiteLogCreateRequest) => siteProgressApi.createLog(payload),
    onSuccess: () => invalidateSiteLogLists(queryClient),
  });
}

export function useUpdateSiteLog() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ logId, payload }: { logId: string; payload: SiteLogUpdateRequest }) =>
      siteProgressApi.updateLog(logId, payload),
    onSuccess: () => invalidateSiteLogLists(queryClient),
  });
}

export function useDeleteSiteLog() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (logId: string) => siteProgressApi.deleteLog(logId),
    onSuccess: () => invalidateSiteLogLists(queryClient),
  });
}