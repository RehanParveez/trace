import { useMutation, useQuery } from "@tanstack/react-query";
import { differenceApi } from "../api/difference.api";
import type { FixList, RunDifference } from "../types/difference.types";

export const differenceKeys = {
  runs: (projectId: string) => ["run-difference", "runs", projectId] as const,
  diff: (from: string, to: string, min: number | undefined) => ["run-difference", "diff", from, to, min ?? null] as const,
  fix: (runId: string) => ["run-difference", "fix-list", runId] as const,
};

export function useComparableRuns(projectId: string | undefined) {
  return useQuery({ queryKey: differenceKeys.runs(projectId ?? ""), queryFn: () => differenceApi.runs(projectId as string), enabled: Boolean(projectId) });
}

export function useRunDifference(fromRunId: string | undefined, toRunId: string | undefined, minChangePct?: number) {
  const ready = Boolean(fromRunId && toRunId && fromRunId !== toRunId);
  return useQuery({
    queryKey: differenceKeys.diff(fromRunId ?? "", toRunId ?? "", minChangePct),
    queryFn: () => differenceApi.difference(fromRunId as string, toRunId as string, minChangePct),
    enabled: ready,
    staleTime: 60 * 1000,
  });
}

export function useExportDifference() {
  return useMutation({ mutationFn: (v: { result: RunDifference; kind: "difference" | "variation" }) => differenceApi.exportDifference(v.result, v.kind) });
}

export function useFixList(runId: string | undefined) {
  return useQuery({ queryKey: differenceKeys.fix(runId ?? ""), queryFn: () => differenceApi.fixList(runId as string), enabled: Boolean(runId) });
}

export function useExportFixList() {
  return useMutation({ mutationFn: (fix: FixList) => differenceApi.exportFixList(fix) });
}
