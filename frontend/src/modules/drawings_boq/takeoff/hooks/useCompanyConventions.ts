import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { companyConventionsApi } from "../api/companyConventions.api";
import type { ConventionsUpdate } from "../types/companyConventions.types";

export const companyConventionKeys = { all: ["company-conventions"] as const };

export function useCompanyConventions(enabled = true) {
  return useQuery({ queryKey: companyConventionKeys.all, queryFn: () => companyConventionsApi.get(), enabled });
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
