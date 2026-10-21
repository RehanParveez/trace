import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readingScoreApi } from "../api/readingScore.api";
import type { ImportLabelsBody, RunScoreBody } from "../types/readingScore.types";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const readingScoreKeys = {
  all: [...takeoffKeys.all, "reading-score"] as const,
  labels: (drawingId: string) => [...takeoffKeys.all, "reading-score", "labels", drawingId] as const,
  template: () => [...takeoffKeys.all, "reading-score", "template"] as const,
  scores: (drawingId: string) => [...takeoffKeys.all, "reading-score", "scores", drawingId] as const,
  score: (scoreId: string) => [...takeoffKeys.all, "reading-score", "score", scoreId] as const,
  compare: (drawingId: string, a: string, b: string) => [...takeoffKeys.all, "reading-score", "compare", drawingId, a, b] as const,
};

export function useReadingLabels(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: readingScoreKeys.labels(drawingId ?? ""),
    queryFn: () => readingScoreApi.labels(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useLabelTemplate(enabled: boolean) {
  return useQuery({ queryKey: readingScoreKeys.template(), queryFn: () => readingScoreApi.template(), enabled, staleTime: Infinity });
}

export function useReadingScores(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: readingScoreKeys.scores(drawingId ?? ""),
    queryFn: () => readingScoreApi.scores(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useReadingScore(scoreId: string | null) {
  return useQuery({
    queryKey: readingScoreKeys.score(scoreId ?? ""),
    queryFn: () => readingScoreApi.score(scoreId as string),
    enabled: Boolean(scoreId),
    staleTime: Infinity,
  });
}

export function useScoreComparison(drawingId: string | undefined, a: string | null, b: string | null) {
  return useQuery({
    queryKey: readingScoreKeys.compare(drawingId ?? "", a ?? "", b ?? ""),
    queryFn: () => readingScoreApi.compare(drawingId as string, a as string, b as string),
    enabled: Boolean(drawingId && a && b && a !== b),
    staleTime: Infinity,
  });
}

export function useDeriveLabels(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => readingScoreApi.derive(drawingId as string),
    onSuccess: (data) => { if (drawingId) qc.setQueryData(readingScoreKeys.labels(drawingId), data.summary); },
  });
}

export function useImportLabels(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ImportLabelsBody) => readingScoreApi.importLabels(drawingId as string, body),
    onSuccess: (data) => { if (drawingId) qc.setQueryData(readingScoreKeys.labels(drawingId), data.summary); },
  });
}

export function useRunReadingScore(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RunScoreBody) => readingScoreApi.run(drawingId as string, body),
    onSuccess: (data) => {
      qc.setQueryData(readingScoreKeys.score(data.id), data);
      if (drawingId) void qc.invalidateQueries({ queryKey: readingScoreKeys.scores(drawingId) });
    },
  });
}
