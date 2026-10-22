import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { gradesApi } from "../api/grades.api";
import type { GradesReport, StampBody } from "../types/grades.types";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const gradesKey = (drawingId: string) => [...takeoffKeys.all, "printed-grades", drawingId] as const;

function useAfterChange(drawingId: string | undefined) {
  const qc = useQueryClient();
  return (report: GradesReport) => {
    if (!drawingId) return;
    qc.setQueryData(gradesKey(drawingId), report);
    void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === takeoffKeys.all[0] && q.queryKey[1] !== "printed-grades" });
  };
}

export function useGrades(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: gradesKey(drawingId ?? ""),
    queryFn: () => gradesApi.report(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useStampGrades(drawingId: string | undefined) {
  const after = useAfterChange(drawingId);
  return useMutation({ mutationFn: (body: StampBody) => gradesApi.stamp(drawingId as string, body), onSuccess: after });
}

export function useUnstampGrades(drawingId: string | undefined) {
  const after = useAfterChange(drawingId);
  return useMutation({ mutationFn: () => gradesApi.unstamp(drawingId as string), onSuccess: after });
}
