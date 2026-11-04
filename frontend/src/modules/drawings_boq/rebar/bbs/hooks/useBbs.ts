import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { drawingsBoqKeys } from "../../../hooks/useDrawingsBoq";
import { bbsApi } from "../api/bbs.api";
import type { FindingDecision, FindingFilters } from "../types/bbsAudit.types";

const K = drawingsBoqKeys.all;
export const bbsKeys = {
  list: (projectId: string) => [...K, "bbs", projectId] as const,
  audit: (documentId: string) => [...K, "bbs-audit", documentId] as const,
  findingsRoot: (documentId: string) => [...K, "bbs-findings", documentId] as const,
  findings: (documentId: string, f: FindingFilters) => [...K, "bbs-findings", documentId, f.finding_class ?? "", f.status ?? "", f.code ?? "", f.page] as const,
};

export function useBbsDocuments(projectId: string) {
  return useQuery({ queryKey: bbsKeys.list(projectId), queryFn: () => bbsApi.list(projectId), enabled: Boolean(projectId) });
}

export function useBbsAuditRun(documentId: string | undefined) {
  return useQuery({ queryKey: bbsKeys.audit(documentId ?? ""), queryFn: () => bbsApi.latestAudit(documentId as string), enabled: Boolean(documentId) });
}

export function useBbsFindings(documentId: string | undefined, filters: FindingFilters) {
  return useQuery({ queryKey: bbsKeys.findings(documentId ?? "", filters), queryFn: () => bbsApi.findings(documentId as string, filters), enabled: Boolean(documentId) });
}

export function useUploadBbs(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => bbsApi.upload(projectId, file),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: bbsKeys.list(projectId) }); },
  });
}

export function useRunBbsAudit(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => bbsApi.runAudit(documentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: bbsKeys.audit(documentId) });
      void qc.invalidateQueries({ queryKey: bbsKeys.findingsRoot(documentId) });
    },
  });
}

export function useRunBbsCrossCheck(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => bbsApi.runCrossCheck(documentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: bbsKeys.audit(documentId) });
      void qc.invalidateQueries({ queryKey: bbsKeys.findingsRoot(documentId) });
    },
  });
}

export function useDecideFinding(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, status, reason }: { findingId: string; status: FindingDecision; reason: string }) => bbsApi.decide(findingId, status, reason),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: bbsKeys.findingsRoot(documentId) }); },
  });
}
