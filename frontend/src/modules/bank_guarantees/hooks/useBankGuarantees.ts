import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bankGuaranteesApi } from "../api/bank-guarantees.api";

export const bankGuaranteeKeys = {
  all: ["bank-guarantees"] as const,
  list: (projectId: string) => [...bankGuaranteeKeys.all, "list", projectId] as const,
  detail: (id: string) => [...bankGuaranteeKeys.all, "detail", id] as const,
  summary: (projectId: string) => [...bankGuaranteeKeys.all, "summary", projectId] as const,
};

export function useBankGuarantees(projectId: string) {
  return useQuery({ queryKey: bankGuaranteeKeys.list(projectId), queryFn: () => bankGuaranteesApi.list(projectId), enabled: Boolean(projectId) });
}

export function useBankGuaranteeSummary(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: bankGuaranteeKeys.summary(projectId),
    queryFn: () => bankGuaranteesApi.getProjectSummary(projectId),
    enabled: Boolean(projectId) && (options?.enabled ?? true),
  });
}

function invalidate(qc: ReturnType<typeof useQueryClient>, projectId: string) {
  void qc.invalidateQueries({ queryKey: bankGuaranteeKeys.list(projectId) });
  void qc.invalidateQueries({ queryKey: bankGuaranteeKeys.summary(projectId) });
}

export function useCreateBankGuarantee(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<Parameters<typeof bankGuaranteesApi.create>[0], "project_id">) =>
      bankGuaranteesApi.create({ ...payload, project_id: projectId }),
    onSuccess: () => invalidate(qc, projectId),
  });
}

export function useRenewBankGuarantee(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof bankGuaranteesApi.renew>[1] }) => bankGuaranteesApi.renew(id, payload),
    onSuccess: () => invalidate(qc, projectId),
  });
}

export function useReleaseBankGuarantee(projectId: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => bankGuaranteesApi.release(id), onSuccess: () => invalidate(qc, projectId) });
}

export function useMarkGuaranteeCalled(projectId: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => bankGuaranteesApi.markCalled(id), onSuccess: () => invalidate(qc, projectId) });
}