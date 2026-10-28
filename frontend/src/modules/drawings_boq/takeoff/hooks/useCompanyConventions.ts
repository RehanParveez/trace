import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { companyConventionsApi } from "../api/companyConventions.api";
import type { ConventionsUpdate, ProjectOverridesUpdate } from "../types/companyConventions.types";

export const companyConventionKeys = { all: ["company-conventions"] as const, project: (projectId: string) => ["company-conventions", "project", projectId] as const };

export function useCompanyConventions(enabled = true, projectId?: string | null) {
  return useQuery({ queryKey: projectId ? companyConventionKeys.project(projectId) : companyConventionKeys.all, queryFn: () => companyConventionsApi.get(projectId), enabled });
}

export function useSaveProjectConventions(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectOverridesUpdate) => companyConventionsApi.saveProject(projectId as string, body),
    onSuccess: (data) => { if (projectId) qc.setQueryData(companyConventionKeys.project(projectId), data); },
  });
}

export function useSaveCompanyConventions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConventionsUpdate) => companyConventionsApi.save(body),
    onSuccess: (data) => qc.setQueryData(companyConventionKeys.all, data),
  });
}

export function useAdoptQsConventions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => companyConventionsApi.adoptQs(),
    onSuccess: (data) => qc.setQueryData(companyConventionKeys.all, data),
  });
}
