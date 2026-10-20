import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { oneTotalApi, type OneTotalRuleBody } from "../api/oneTotal.api";
import { drawingsBoqKeys } from "./useDrawingsBoq";

export const oneTotalKeys = {
  rules: (projectId: string) => [...drawingsBoqKeys.all, "one-total-rules", projectId] as const,
  sources: (projectId: string) => [...drawingsBoqKeys.all, "one-total-sources", projectId] as const,
};

export function useOneTotalRules(projectId: string | undefined) {
  return useQuery({ queryKey: oneTotalKeys.rules(projectId ?? ""), queryFn: () => oneTotalApi.rules(projectId as string), enabled: Boolean(projectId) });
}

export function useSetOneTotalRule(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: OneTotalRuleBody) => oneTotalApi.setRule(projectId as string, body),
    onSuccess: (rules) => {
      queryClient.setQueryData(oneTotalKeys.rules(projectId ?? ""), rules);
      void queryClient.invalidateQueries({ queryKey: oneTotalKeys.sources(projectId ?? "") });
    },
  });
}

export function useRemoveOneTotalRule(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => oneTotalApi.removeRule(projectId as string, ruleId),
    onSuccess: (rules) => {
      queryClient.setQueryData(oneTotalKeys.rules(projectId ?? ""), rules);
      void queryClient.invalidateQueries({ queryKey: oneTotalKeys.sources(projectId ?? "") });
    },
  });
}

export function useOneTotalSources(projectId: string | undefined) {
  return useQuery({ queryKey: oneTotalKeys.sources(projectId ?? ""), queryFn: () => oneTotalApi.sources(projectId as string), enabled: Boolean(projectId), staleTime: 30 * 1000 });
}
