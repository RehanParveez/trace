import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { decisionsApi } from "../api/decisions.api";
import { takeoffApi } from "../../api/takeoff.api";
import { takeoffKeys } from "../../hooks/useTakeoff";
import type { ChooseDecisionBody, DecisionsReport } from "../types/decisions.types";

export const decisionsKey = (drawingId: string, version: number) => [...takeoffKeys.all, "decisions", drawingId, version] as const;

export function useDecisions(drawingId: string | undefined, version = 0, enabled = true) {
  return useQuery({
    queryKey: decisionsKey(drawingId ?? "", version),
    queryFn: () => decisionsApi.report(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
    placeholderData: keepPreviousData,
  });
}

function useAfterChange(drawingId: string | undefined) {
  const qc = useQueryClient();
  return () => {
    if (!drawingId) return;
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "decisions", drawingId] });
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "review"] });
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "integrity", drawingId] });
  };
}

export function useChooseDecision(drawingId: string | undefined) {
  const after = useAfterChange(drawingId);
  return useMutation({
    mutationFn: (body: ChooseDecisionBody): Promise<DecisionsReport> => decisionsApi.choose(drawingId as string, body),
    onSettled: after,
  });
}

export function useReadAfterDecision(drawingId: string | undefined) {
  const qc = useQueryClient();
  const after = useAfterChange(drawingId);
  return useMutation({
    mutationFn: async () => {
      let guard = 0;
      let out = await takeoffApi.extractDrawing(drawingId as string, { auto_calibrate: true, only_unread: true });
      while (out.skipped.some((s) => s.code === "TIME_BUDGET") && out.done.length > 0 && guard < 8) {
        guard += 1;
        out = await takeoffApi.extractDrawing(drawingId as string, { auto_calibrate: true, only_unread: true });
      }
      return out;
    },
    onSettled: () => {
      after();
      if (!drawingId) return;
      void qc.invalidateQueries({ queryKey: takeoffKeys.overview(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.crossChecks(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.ready(drawingId) });
      void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
    },
  });
}
