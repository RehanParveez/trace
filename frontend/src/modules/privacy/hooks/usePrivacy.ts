import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { privacyApi } from "../api/privacy.api";
import type {DeletionRequestCreate, ExportJob, SupportGrantCreateRequest,
} from "../types/privacy.types";

export const privacyKeys = {
  all: ["privacy"] as const,
  overview: () => [...privacyKeys.all, "overview"] as const,
  grants: () => [...privacyKeys.all, "support-grants"] as const,
  exports: () => [...privacyKeys.all, "exports"] as const,
};

const IN_FLIGHT = new Set(["QUEUED", "RUNNING"]);

function useInvalidateAll() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: privacyKeys.all });
}

export function usePrivacyOverview() {
  return useQuery({
    queryKey: privacyKeys.overview(),
    queryFn: privacyApi.getOverview,
  });
}

export function useSupportGrants() {
  return useQuery({
    queryKey: privacyKeys.grants(),
    queryFn: privacyApi.listSupportGrants,
  });
}

export function useCreateSupportGrant() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (payload: SupportGrantCreateRequest) =>
      privacyApi.createSupportGrant(payload),
    onSuccess: invalidate,
  });
}

export function useRevokeSupportGrant() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (grantId: string) => privacyApi.revokeSupportGrant(grantId),
    onSuccess: invalidate,
  });
}

export function useExports() {
  return useQuery({
    queryKey: privacyKeys.exports(),
    queryFn: privacyApi.listExports,
    refetchInterval: (query) => {
      const jobs = query.state.data as ExportJob[] | undefined;
      return jobs?.some((job) => IN_FLIGHT.has(job.status)) ? 4000 : false;
    },
  });
}

export function useRequestExport() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => privacyApi.requestExport(),
    onSuccess: invalidate,
  });
}

export function useDownloadExport() {
  return useMutation({
    mutationFn: (jobId: string) => privacyApi.getExportDownload(jobId),
  });
}

export function useRequestDeletion() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (payload: DeletionRequestCreate) => privacyApi.requestDeletion(payload),
    onSuccess: invalidate,
  });
}

export function useCancelDeletion() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: () => privacyApi.cancelDeletion(),
    onSuccess: invalidate,
  });
}
