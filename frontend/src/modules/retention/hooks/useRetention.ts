import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { retentionApi } from "../api/retention.api";

export const retentionKeys = {
  all: ["retention"] as const,
  releases: (projectId?: string) => [...retentionKeys.all, "releases", projectId] as const,
  projectSummary: (projectId: string) => [...retentionKeys.all, "project-summary", projectId] as const,
  orgSummary: () => [...retentionKeys.all, "org-summary"] as const,
};

export function useRetentionReleases(projectId?: string) {
  return useQuery({ queryKey: retentionKeys.releases(projectId), queryFn: () => retentionApi.listReleases(projectId) });
}

export function useCreateRetentionRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof retentionApi.recordRelease>[0]) => retentionApi.recordRelease(payload),
    onSuccess: (release) => {
      void qc.invalidateQueries({ queryKey: retentionKeys.releases(release.project_id) });
      void qc.invalidateQueries({ queryKey: retentionKeys.projectSummary(release.project_id) });
      void qc.invalidateQueries({ queryKey: retentionKeys.orgSummary() });
    },
  });
}

export function useProjectRetentionSummary(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: retentionKeys.projectSummary(projectId),
    queryFn: () => retentionApi.getProjectSummary(projectId),
    enabled: Boolean(projectId) && (options?.enabled ?? true),
  });
}

export function useOrganizationRetentionSummary(options?: { enabled?: boolean }) {
  return useQuery({ queryKey: retentionKeys.orgSummary(), queryFn: retentionApi.getOrganizationSummary, enabled: options?.enabled });
}