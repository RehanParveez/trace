import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { finishRulesApi } from "../api/finishRules.api";
import type { FinishRulesUpdate } from "../types/finishRules.types";

export const finishRuleKeys = { project: (projectId: string) => ["finish-rules", projectId] as const };

export function useProjectFinishRules(projectId: string | undefined) {
  return useQuery({ queryKey: finishRuleKeys.project(projectId ?? ""), queryFn: () => finishRulesApi.get(projectId as string), enabled: Boolean(projectId) });
}

export function useSaveProjectFinishRules(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FinishRulesUpdate) => finishRulesApi.save(projectId as string, body),
    onSuccess: (data) => { if (projectId) qc.setQueryData(finishRuleKeys.project(projectId), data); },
  });
}
