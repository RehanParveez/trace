import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { drawingsBoqKeys } from "../../../hooks/useDrawingsBoq";
import { bbsExpectApi } from "../api/bbsExpect.api";
import type { ExpectFilters } from "../types/bbsExpect.types";
import { bbsMatchKeys } from "./useBbsMatch";

const K = drawingsBoqKeys.all;
export const bbsExpectKeys = {
  run: (documentId: string) => [...K, "bbs-expect", documentId] as const,
  itemsRoot: (documentId: string) => [...K, "bbs-expect-items", documentId] as const,
  items: (documentId: string, f: ExpectFilters) => [...K, "bbs-expect-items", documentId, f.member_class, f.complete, f.page] as const,
};

export function useBbsExpectRun(documentId: string | undefined) {
  return useQuery({ queryKey: bbsExpectKeys.run(documentId ?? ""), queryFn: () => bbsExpectApi.latest(documentId as string), enabled: Boolean(documentId) });
}

export function useBbsExpectItems(documentId: string | undefined, filters: ExpectFilters) {
  return useQuery({ queryKey: bbsExpectKeys.items(documentId ?? "", filters), queryFn: () => bbsExpectApi.items(documentId as string, filters), enabled: Boolean(documentId) });
}

export function useRunBbsExpect(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => bbsExpectApi.run(documentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: bbsExpectKeys.run(documentId) });
      void qc.invalidateQueries({ queryKey: bbsExpectKeys.itemsRoot(documentId) });
    },
  });
}

export function useSaveDecision(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) => (value === null ? bbsExpectApi.clearDecision(projectId, key) : bbsExpectApi.putDecision(projectId, key, value)),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: bbsMatchKeys.decisions(projectId) }); },
  });
}
