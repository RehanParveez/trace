import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { detailOnlyApi } from "../api/detailOnly.api";
import type { ChooseDepthBody, ChooseMarkBody } from "../types/detailOnly.types";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const detailOnlyKey = (drawingId: string) => [...takeoffKeys.all, "detail-only", drawingId] as const;

const ITEM_QUERIES = ["candidates", "overview", "ready", "checks"];

function useAfterChoice(drawingId: string | undefined) {
  const qc = useQueryClient();
  return (report: unknown) => {
    if (!drawingId) return;
    qc.setQueryData(detailOnlyKey(drawingId), report);
    void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === takeoffKeys.all[0] && ITEM_QUERIES.includes(String(q.queryKey[1])) });
  };
}

export function useDetailOnly(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: detailOnlyKey(drawingId ?? ""),
    queryFn: () => detailOnlyApi.report(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useChooseColumnMark(drawingId: string | undefined) {
  const after = useAfterChoice(drawingId);
  return useMutation({ mutationFn: (body: ChooseMarkBody) => detailOnlyApi.chooseMark(drawingId as string, body), onSuccess: after });
}

export function useChooseBeamDepth(drawingId: string | undefined) {
  const after = useAfterChoice(drawingId);
  return useMutation({ mutationFn: (body: ChooseDepthBody) => detailOnlyApi.chooseDepth(drawingId as string, body), onSuccess: after });
}

export function useUndoDetailChoice(drawingId: string | undefined) {
  const after = useAfterChoice(drawingId);
  return useMutation({ mutationFn: (decisionId: string) => detailOnlyApi.undo(drawingId as string, decisionId), onSuccess: after });
}
