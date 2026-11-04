import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { drawingsBoqKeys } from "../../../hooks/useDrawingsBoq";
import { bbsMatchApi } from "../api/bbsMatch.api";
import type { ConfirmPayload, MatchFilters } from "../types/bbsMatch.types";

const K = drawingsBoqKeys.all;
export const bbsMatchKeys = {
  run: (documentId: string) => [...K, "bbs-match", documentId] as const,
  itemsRoot: (documentId: string) => [...K, "bbs-match-items", documentId] as const,
  items: (documentId: string, f: MatchFilters) => [...K, "bbs-match-items", documentId, f.kind, f.family, f.page] as const,
  decisions: (projectId: string) => [...K, "bbs-decisions", projectId] as const,
};

export function useBbsMatchRun(documentId: string | undefined) {
  return useQuery({ queryKey: bbsMatchKeys.run(documentId ?? ""), queryFn: () => bbsMatchApi.latest(documentId as string), enabled: Boolean(documentId) });
}

export function useBbsMatchItems(documentId: string | undefined, filters: MatchFilters) {
  return useQuery({ queryKey: bbsMatchKeys.items(documentId ?? "", filters), queryFn: () => bbsMatchApi.items(documentId as string, filters), enabled: Boolean(documentId) });
}

export function useBbsDecisions(projectId: string) {
  return useQuery({ queryKey: bbsMatchKeys.decisions(projectId), queryFn: () => bbsMatchApi.decisions(projectId), enabled: Boolean(projectId) });
}

function useRefresh(documentId: string, projectId: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: bbsMatchKeys.run(documentId) });
    void qc.invalidateQueries({ queryKey: bbsMatchKeys.itemsRoot(documentId) });
    void qc.invalidateQueries({ queryKey: bbsMatchKeys.decisions(projectId) });
  };
}

export function useRunBbsMatch(documentId: string, projectId: string) {
  const refresh = useRefresh(documentId, projectId);
  return useMutation({ mutationFn: () => bbsMatchApi.run(documentId), onSuccess: refresh });
}

export function useConfirmBbsMatch(documentId: string, projectId: string) {
  const refresh = useRefresh(documentId, projectId);
  return useMutation({ mutationFn: (payload: ConfirmPayload) => bbsMatchApi.confirm(documentId, payload), onSuccess: refresh });
}

export function useForgetBbsMatch(documentId: string, projectId: string) {
  const refresh = useRefresh(documentId, projectId);
  return useMutation({ mutationFn: (group: string) => bbsMatchApi.forget(documentId, group), onSuccess: refresh });
}

export function useSaveFloorMap(documentId: string, projectId: string) {
  const refresh = useRefresh(documentId, projectId);
  return useMutation({
    mutationFn: async (value: Record<string, string[]>) => {
      await bbsMatchApi.putFloorMap(projectId, value);
      return bbsMatchApi.run(documentId);
    },
    onSuccess: refresh,
  });
}
