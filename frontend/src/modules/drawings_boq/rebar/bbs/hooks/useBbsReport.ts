import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bbsApi } from "../api/bbs.api";
import { bbsReportApi } from "../api/bbsReport.api";
import type { FindingDecision } from "../types/bbsAudit.types";
import type { ReportFilters } from "../types/bbsReport.types";
import { bbsKeys } from "./useBbs";

export const bbsReportKeys = {
  summary: (documentId: string) => [...bbsKeys.findingsRoot(documentId), "report-summary"] as const,
  questions: (documentId: string) => [...bbsKeys.findingsRoot(documentId), "report-questions"] as const,
  findings: (documentId: string, f: ReportFilters) => [...bbsKeys.findingsRoot(documentId), "report-findings", f.finding_class ?? "", f.status ?? "", f.sheet ?? -1, f.page] as const,
  crops: (findingId: string) => ["bbs-crops", findingId] as const,
};

export function useReportSummary(documentId: string) {
  return useQuery({ queryKey: bbsReportKeys.summary(documentId), queryFn: () => bbsReportApi.summary(documentId) });
}

export function useReportFindings(documentId: string, filters: ReportFilters) {
  return useQuery({ queryKey: bbsReportKeys.findings(documentId, filters), queryFn: () => bbsReportApi.findings(documentId, filters) });
}

export function useReportQuestions(documentId: string) {
  return useQuery({ queryKey: bbsReportKeys.questions(documentId), queryFn: () => bbsReportApi.questions(documentId) });
}

export function useFindingCrops(findingId: string, enabled: boolean) {
  return useQuery({ queryKey: bbsReportKeys.crops(findingId), queryFn: () => bbsReportApi.crops(findingId), enabled, staleTime: Infinity, retry: 1 });
}

export function useDecideReportFinding(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, status, reason }: { findingId: string; status: FindingDecision; reason: string }) => bbsApi.decide(findingId, status, reason),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: bbsKeys.findingsRoot(documentId) }); },
  });
}

export function useSignFinding(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, reason }: { findingId: string; reason: string }) => bbsReportApi.sign(findingId, reason),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: bbsKeys.findingsRoot(documentId) }); },
  });
}
