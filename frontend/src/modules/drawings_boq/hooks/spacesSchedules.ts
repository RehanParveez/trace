import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { spacesSchedulesApi as api } from "../api/drawings-boq.api";
import type {RowDecision, ScheduleFromPdfRequest, ScheduleKind, ScheduleManualCreateRequest, ScheduleRowCreateRequest, ScheduleRowUpdateRequest, SpaceCreateRequest, SpaceFinishCreateRequest,
  SpaceListFilters, SpaceUpdateRequest,
} from "../types/drawings-boq.types";

export const ssKeys = {
  spacesRoot: ["spaces"] as const,
  spaces: (projectId: string, f: SpaceListFilters) =>
    ["spaces", projectId, f] as const,
  spaceRoot: ["space"] as const,
  space: (id: string) => ["space", id] as const,
  finishes: (spaceId: string) => ["space-finishes", spaceId] as const,
  previewRoot: ["space-preview"] as const,
  preview: (spaceId: string, rule?: string) =>
    ["space-preview", spaceId, rule ?? ""] as const,
  levels: (drawingId: string) => ["drawing-levels", drawingId] as const,
  candidates: (drawingId: string) =>
    ["boundary-candidates", drawingId] as const,
  importsRoot: ["schedule-imports"] as const,
  imports: (projectId: string, status?: string) =>
    ["schedule-imports", projectId, status ?? ""] as const,
  importDetail: (id: string) => ["schedule-import", id] as const,
};

export function useSpaces(projectId: string, filters: SpaceListFilters = {}) {
  return useQuery({
    queryKey: ssKeys.spaces(projectId, filters),
    queryFn: () => api.listSpaces(projectId, filters),
    enabled: !!projectId,
  });
}

export function useSpace(spaceId: string | undefined) {
  return useQuery({
    queryKey: ssKeys.space(spaceId ?? ""),
    queryFn: () => api.getSpace(spaceId as string),
    enabled: !!spaceId,
  });
}

export function useSpaceFinishes(spaceId: string | undefined) {
  return useQuery({
    queryKey: ssKeys.finishes(spaceId ?? ""),
    queryFn: () => api.listFinishes(spaceId as string),
    enabled: !!spaceId,
  });
}

export function useFinishPreview(
  spaceId: string | undefined,
  ruleSetCode?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ssKeys.preview(spaceId ?? "", ruleSetCode),
    queryFn: () => api.previewFinishes(spaceId as string, ruleSetCode),
    enabled: !!spaceId && enabled,
  });
}

export function useDrawingLevels(drawingId: string | undefined) {
  return useQuery({
    queryKey: ssKeys.levels(drawingId ?? ""),
    queryFn: () => api.listLevels(drawingId as string),
    enabled: !!drawingId,
  });
}

export function useBoundaryCandidates(
  drawingId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: ssKeys.candidates(drawingId ?? ""),
    queryFn: () => api.listBoundaryCandidates(drawingId as string),
    enabled: !!drawingId && enabled,
    staleTime: 60_000,
  });
}

export function useScheduleImports(projectId: string, status?: string) {
  return useQuery({
    queryKey: ssKeys.imports(projectId, status),
    queryFn: () => api.listImports(projectId, status),
    enabled: !!projectId,
  });
}

export function useScheduleImport(importId: string | undefined) {
  return useQuery({
    queryKey: ssKeys.importDetail(importId ?? ""),
    queryFn: () => api.getImport(importId as string),
    enabled: !!importId,
  });
}

function useSpaceInvalidator() {
  const qc = useQueryClient();
  return (spaceId?: string) => {
    void qc.invalidateQueries({ queryKey: ssKeys.spacesRoot });
    void qc.invalidateQueries({ queryKey: ssKeys.previewRoot });
    if (spaceId) {
      void qc.invalidateQueries({ queryKey: ssKeys.space(spaceId) });
      void qc.invalidateQueries({ queryKey: ssKeys.finishes(spaceId) });
    } else {
      void qc.invalidateQueries({ queryKey: ssKeys.spaceRoot });
    }
  };
}

export function useCreateSpace(projectId: string) {
  const invalidate = useSpaceInvalidator();
  return useMutation({
    mutationFn: (body: SpaceCreateRequest) => api.createSpace(projectId, body),
    onSuccess: () => invalidate(),
  });
}

export function useUpdateSpace(spaceId: string) {
  const invalidate = useSpaceInvalidator();
  return useMutation({
    mutationFn: (body: SpaceUpdateRequest) => api.updateSpace(spaceId, body),
    onSuccess: () => invalidate(spaceId),
  });
}

export function useDeleteSpace() {
  const invalidate = useSpaceInvalidator();
  return useMutation({
    mutationFn: (spaceId: string) => api.deleteSpace(spaceId),
    onSuccess: () => invalidate(),
  });
}

export function useSetBoundaries(spaceId: string) {
  const invalidate = useSpaceInvalidator();
  return useMutation({
    mutationFn: (elementIds: string[]) => api.setBoundaries(spaceId, elementIds),
    onSuccess: () => invalidate(spaceId),
  });
}

export function useUpsertFinish(spaceId: string) {
  const invalidate = useSpaceInvalidator();
  return useMutation({
    mutationFn: (body: SpaceFinishCreateRequest) =>
      api.upsertFinish(spaceId, body),
    onSuccess: () => invalidate(spaceId),
  });
}

export function useDeleteFinish(spaceId: string) {
  const invalidate = useSpaceInvalidator();
  return useMutation({
    mutationFn: (finishId: string) => api.deleteFinish(finishId),
    onSuccess: () => invalidate(spaceId),
  });
}

function useImportInvalidator() {
  const qc = useQueryClient();
  return (importId?: string) => {
    void qc.invalidateQueries({ queryKey: ssKeys.importsRoot });
    if (importId) {
      void qc.invalidateQueries({ queryKey: ssKeys.importDetail(importId) });
    }
  };
}

export function useImportScheduleFile(projectId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (v: { file: File; kind: ScheduleKind; notes?: string | null }) =>
      api.importFile(projectId, v.file, v.kind, v.notes),
    onSuccess: () => invalidate(),
  });
}

export function useImportScheduleFromPdf(projectId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (body: ScheduleFromPdfRequest) =>
      api.importFromPdf(projectId, body),
    onSuccess: () => invalidate(),
  });
}

export function useCreateManualImport(projectId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (body: ScheduleManualCreateRequest) =>
      api.createManualImport(projectId, body),
    onSuccess: () => invalidate(),
  });
}

export function useAddScheduleRow(importId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (body: ScheduleRowCreateRequest) => api.addRow(importId, body),
    onSuccess: () => invalidate(importId),
  });
}

export function useUpdateScheduleRow(importId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (v: { rowId: string; body: ScheduleRowUpdateRequest }) =>
      api.updateRow(v.rowId, v.body),
    onSuccess: () => invalidate(importId),
  });
}

export function useBulkReview(importId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (v: { rowIds: string[]; decision: RowDecision }) =>
      api.bulkReview(importId, v.rowIds, v.decision),
    onSuccess: () => invalidate(importId),
  });
}

export function useConfirmImport(importId: string) {
  const qc = useQueryClient();
  const invalidate = useImportInvalidator();
  const invalidateSpaces = useSpaceInvalidator();
  return useMutation({
    mutationFn: (rejectPending: boolean) =>
      api.confirmImport(importId, rejectPending),
    onSuccess: () => {
      invalidate(importId);
      invalidateSpaces();
      void qc;
    },
  });
}

export function useRejectImport(importId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: (note?: string | null) => api.rejectImport(importId, note),
    onSuccess: () => invalidate(importId),
  });
}

export function useArchiveImport(importId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: () => api.archiveImport(importId),
    onSuccess: () => invalidate(importId),
  });
}

export function useRematchImport(importId: string) {
  const invalidate = useImportInvalidator();
  return useMutation({
    mutationFn: () => api.rematchImport(importId),
    onSuccess: () => invalidate(importId),
  });
}