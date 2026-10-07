import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { rebarApi } from "../api/rebar.api";
import { drawingsBoqKeys } from "../../hooks/useDrawingsBoq";
import type { RebarRowUpdateRequest, RowDecision } from "../../types/drawings-boq.types";

const K = drawingsBoqKeys.all;
export const rebarKeys = {
  importsRoot: (projectId: string) => [...K, "rebar-imports", projectId] as const,
  imports: (projectId: string, status?: string) => [...K, "rebar-imports", projectId, status ?? "all"] as const,
  importDetail: (importId: string) => [...K, "rebar-import", importId] as const,
  shapes: () => [...K, "rebar-shapes"] as const,
  sizes: () => [...K, "bar-sizes"] as const,
  summary: (versionId: string) => [...K, "rebar-summary", versionId] as const,
};

export function useRebarImports(projectId: string, status?: string) {
  return useQuery({ queryKey: rebarKeys.imports(projectId, status), queryFn: () => rebarApi.listImports(projectId, status), enabled: Boolean(projectId) });
}

export function useRebarImportDetail(importId: string | undefined) {
  return useQuery({ queryKey: rebarKeys.importDetail(importId ?? ""), queryFn: () => rebarApi.getImport(importId as string), enabled: Boolean(importId) });
}

export function useRebarShapes(enabled = true) {
  return useQuery({ queryKey: rebarKeys.shapes(), queryFn: () => rebarApi.listShapes(), enabled, staleTime: 300_000 });
}

export function useBarSizes(enabled = true) {
  return useQuery({ queryKey: rebarKeys.sizes(), queryFn: () => rebarApi.listSizes(), enabled, staleTime: 300_000 });
}

export function useRebarSummary(versionId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: rebarKeys.summary(versionId ?? ""),
    queryFn: () => rebarApi.summary(versionId as string),
    enabled: Boolean(versionId) && enabled,
    retry: false,
  });
}

function useRefreshRebar(projectId: string, importId?: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: rebarKeys.importsRoot(projectId) });
    if (importId) void qc.invalidateQueries({ queryKey: rebarKeys.importDetail(importId) });
  };
}

export function useImportRebarFile(projectId: string) {
  const refresh = useRefreshRebar(projectId);
  return useMutation({
    mutationFn: ({ file, notes }: { file: File; notes?: string | null }) => rebarApi.importFile(projectId, file, notes),
    onSuccess: refresh,
  });
}

export function useImportRebarPdf(projectId: string) {
  const refresh = useRefreshRebar(projectId);
  return useMutation({
    mutationFn: ({ drawingId, notes }: { drawingId: string; notes?: string | null }) => rebarApi.importFromPdf(projectId, drawingId, notes),
    onSuccess: refresh,
  });
}

export function useUpdateRebarRow(projectId: string, importId: string) {
  const refresh = useRefreshRebar(projectId, importId);
  return useMutation({
    mutationFn: ({ rowId, payload }: { rowId: string; payload: RebarRowUpdateRequest }) => rebarApi.updateRow(rowId, payload),
    onSuccess: refresh,
  });
}

export function useBulkReviewRebarRows(projectId: string, importId: string) {
  const refresh = useRefreshRebar(projectId, importId);
  return useMutation({
    mutationFn: ({ rowIds, decision }: { rowIds: string[]; decision: RowDecision }) => rebarApi.bulkReview(importId, rowIds, decision),
    onSuccess: refresh,
  });
}

export function useConfirmRebarImport(projectId: string, importId: string) {
  const refresh = useRefreshRebar(projectId, importId);
  return useMutation({ mutationFn: (rejectPending: boolean) => rebarApi.confirmImport(importId, rejectPending), onSuccess: refresh });
}

export function useRejectRebarImport(projectId: string, importId: string) {
  const refresh = useRefreshRebar(projectId, importId);
  return useMutation({ mutationFn: () => rebarApi.rejectImport(importId), onSuccess: refresh });
}

export function useArchiveRebarImport(projectId: string, importId: string) {
  const refresh = useRefreshRebar(projectId, importId);
  return useMutation({ mutationFn: () => rebarApi.archiveImport(importId), onSuccess: refresh });
}
