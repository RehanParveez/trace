import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { takeoffKeys } from "../../hooks/useTakeoff";
import { flowApi } from "../api/flow.api";
import type { AccuracyReport, ExportKind, FlowBoq, FlowStatus, RateBookOption, SeenStep } from "../types/flow.types";

export const flowKeys = {
  all: [...takeoffKeys.all, "flow"] as const,
  status: (projectId: string, profile: string | null) => [...takeoffKeys.all, "flow", "status", projectId, profile ?? ""] as const,
  boq: (projectId: string, profile: string | null, book: string | null) => [...takeoffKeys.all, "flow", "boq", projectId, profile ?? "", book ?? ""] as const,
  accuracy: (projectId: string, profile: string | null, book: string | null) => [...takeoffKeys.all, "flow", "accuracy", projectId, profile ?? "", book ?? ""] as const,
  books: () => [...takeoffKeys.all, "flow", "rate-books"] as const,
};

const POLL_MS = 3000;

export function useFlowStatus(projectId: string | undefined, profile: string | null) {
  return useQuery<FlowStatus>({
    queryKey: flowKeys.status(projectId ?? "", profile),
    queryFn: () => flowApi.status(projectId as string, profile),
    enabled: Boolean(projectId),
    refetchInterval: (query) => (query.state.data?.steps.some((s) => s.state === "RUNNING") ? POLL_MS : false),
  });
}

export function useFlowBoq(projectId: string | undefined, profile: string | null, rateBookId: string | null, enabled: boolean) {
  return useQuery<FlowBoq>({
    queryKey: flowKeys.boq(projectId ?? "", profile, rateBookId),
    queryFn: () => flowApi.boq(projectId as string, profile, rateBookId),
    enabled: Boolean(projectId) && enabled,
  });
}

export function useFlowAccuracy(projectId: string | undefined, profile: string | null, rateBookId: string | null, enabled: boolean) {
  return useQuery<AccuracyReport>({
    queryKey: flowKeys.accuracy(projectId ?? "", profile, rateBookId),
    queryFn: () => flowApi.accuracy(projectId as string, profile, rateBookId),
    enabled: Boolean(projectId) && enabled,
  });
}

export function useRateBooks() {
  return useQuery<RateBookOption[]>({ queryKey: flowKeys.books(), queryFn: flowApi.rateBooks });
}

export function useFlowSeen(projectId: string | undefined) {
  return useMutation<void, unknown, SeenStep>({ mutationFn: (step) => flowApi.seen(projectId as string, step) });
}

function useStepAction<V>(projectId: string | undefined, run: (id: string, value: V) => Promise<void>) {
  const qc = useQueryClient();
  return useMutation<void, unknown, V>({
    mutationFn: (value) => run(projectId as string, value),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: takeoffKeys.all });
    },
  });
}

export function useUploadDrawing(projectId: string | undefined) {
  return useStepAction<File>(projectId, flowApi.upload);
}

export function useStartRead(projectId: string | undefined) {
  return useStepAction<void>(projectId, (id) => flowApi.startRead(id));
}

export function useStartQuantities(projectId: string | undefined) {
  return useStepAction<void>(projectId, (id) => flowApi.startQuantities(id));
}

export function useExport(projectId: string | undefined, profile: string | null, rateBookId: string | null) {
  const qc = useQueryClient();
  return useMutation<{ blob: Blob; name: string }, unknown, ExportKind>({
    mutationFn: (kind) => flowApi.download(projectId as string, kind, profile, rateBookId),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: flowKeys.all });
    },
  });
}
