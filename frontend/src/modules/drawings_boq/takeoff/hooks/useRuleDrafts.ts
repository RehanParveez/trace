import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ruleDraftsApi } from "../api/ruleDrafts.api";
import { companyConventionKeys } from "./useCompanyConventions";
import type { DraftFile } from "../types/ruleDrafts.types";

export const ruleDraftKeys = { all: ["rule-book-drafts"] as const };

export function useRuleDrafts(enabled = true) {
  return useQuery({ queryKey: ruleDraftKeys.all, queryFn: () => ruleDraftsApi.list(), enabled });
}

export function useImportRuleDrafts() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (body: DraftFile) => ruleDraftsApi.import(body), onSuccess: (data) => qc.setQueryData(ruleDraftKeys.all, data) });
}

export function useConfirmRuleDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; value?: unknown }) => ruleDraftsApi.confirm(v.id, v.value),
    onSuccess: (data) => { qc.setQueryData(ruleDraftKeys.all, data); void qc.invalidateQueries({ queryKey: companyConventionKeys.all }); },
  });
}

export function useRejectRuleDraft() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => ruleDraftsApi.reject(id), onSuccess: (data) => qc.setQueryData(ruleDraftKeys.all, data) });
}
