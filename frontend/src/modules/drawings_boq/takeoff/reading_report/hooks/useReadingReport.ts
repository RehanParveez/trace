import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readingReportApi } from "../api/readingReport.api";
import type { ManualMarkBody, MisreadBody } from "../types/readingReport.types";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const readingReportKeys = {
  all: [...takeoffKeys.all, "reading-report"] as const,
  report: (drawingId: string) => [...takeoffKeys.all, "reading-report", "report", drawingId] as const,
  items: (drawingId: string, sheetId: string) => [...takeoffKeys.all, "reading-report", "items", drawingId, sheetId] as const,
  completeness: (projectId: string) => [...takeoffKeys.all, "reading-report", "completeness", projectId] as const,
  marks: (drawingId: string, sheetId: string) => [...takeoffKeys.all, "reading-report", "marks", drawingId, sheetId] as const,
};

export function useReadingReport(drawingId: string | undefined) {
  return useQuery({ queryKey: readingReportKeys.report(drawingId ?? ""), queryFn: () => readingReportApi.report(drawingId as string), enabled: Boolean(drawingId) });
}

export function useSheetItems(drawingId: string | undefined, sheetId: string | null) {
  return useQuery({
    queryKey: readingReportKeys.items(drawingId ?? "", sheetId ?? ""),
    queryFn: () => readingReportApi.items(drawingId as string, sheetId as string),
    enabled: Boolean(drawingId && sheetId),
  });
}

export function useInputCompleteness(projectId: string | undefined) {
  return useQuery({ queryKey: readingReportKeys.completeness(projectId ?? ""), queryFn: () => readingReportApi.completeness(projectId as string), enabled: Boolean(projectId) });
}

export function useSheetMarks(drawingId: string | undefined, sheetId: string | null) {
  return useQuery({
    queryKey: readingReportKeys.marks(drawingId ?? "", sheetId ?? ""),
    queryFn: () => readingReportApi.marks(drawingId as string, sheetId as string),
    enabled: Boolean(drawingId && sheetId),
  });
}

export function useAddMark(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ManualMarkBody) => readingReportApi.addMark(drawingId as string, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: readingReportKeys.all }),
  });
}

export function useWithdrawMark(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => readingReportApi.withdrawMark(drawingId as string, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: readingReportKeys.all }),
  });
}

export function useReportMisread(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MisreadBody) => readingReportApi.reportMisread(drawingId as string, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: readingReportKeys.report(drawingId ?? "") }),
  });
}
