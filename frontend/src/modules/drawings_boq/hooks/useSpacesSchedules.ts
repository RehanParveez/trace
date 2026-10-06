import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { spacesSchedulesApi as api } from "../api/drawings-boq.api";
import { drawingsBoqKeys } from "./useDrawingsBoq";
import type { Drawing } from "../types/drawings-boq.types";
import type {LevelOption, RowDecision, ScheduleFromPdfRequest, ScheduleKind, ScheduleManualCreateRequest, ScheduleRowCreateRequest, ScheduleRowUpdateRequest, SpaceCreateRequest, SpaceFinishCreateRequest, SpaceListFilters, SpaceUpdateRequest,
} from "../types/drawings-boq.types";

const K = drawingsBoqKeys.all;
export const spaceKeys = {
  levels: (drawingId: string) => [...K, "levels", drawingId] as const,
  candidates: (drawingId: string) => [...K, "boundary-candidates", drawingId] as const,
  spacesRoot: (projectId: string) => [...K, "spaces", projectId] as const,
  spaces: (projectId: string, f: SpaceListFilters) => [...K, "spaces", projectId, JSON.stringify(f)] as const,
  detailRoot: () => [...K, "space"] as const,
  detail: (spaceId: string) => [...K, "space", spaceId] as const,
  preview: (spaceId: string, code: string) => [...K, "finish-preview", spaceId, code] as const,
  imports: (projectId: string, status?: string) => [...K, "schedule-imports", projectId, status ?? "all"] as const,
  importsRoot: (projectId: string) => [...K, "schedule-imports", projectId] as const,
  importDetail: (importId: string) => [...K, "schedule-import", importId] as const,
};

export function useProjectLevels(drawings: Pick<Drawing, "id" | "format" | "status" | "is_current_revision">[]): LevelOption[] {
  const ids = drawings.filter((d) => d.is_current_revision && d.format === "IFC" && d.status === "PARSED").map((d) => d.id);
  const results = useQueries({ queries: ids.map((id) => ({ queryKey: spaceKeys.levels(id), queryFn: () => api.listLevels(id), staleTime: 60_000 })) });
  const seen = new Map<string, LevelOption>();
  for (const r of results) for (const l of r.data ?? []) if (!seen.has(l.id)) seen.set(l.id, l);
  return [...seen.values()].sort((a, b) => a.sequence - b.sequence);
}

export function useBoundaryCandidates(drawingId: string | undefined) {
  return useQuery({ queryKey: spaceKeys.candidates(drawingId ?? ""), queryFn: () => api.listBoundaryCandidates(drawingId as string), enabled: Boolean(drawingId) });
}

export function useSpaces(projectId: string, f: SpaceListFilters) {
  return useQuery({ queryKey: spaceKeys.spaces(projectId, f), queryFn: () => api.listSpaces(projectId, f), enabled: Boolean(projectId) });
}

export function useSpaceDetail(spaceId: string | undefined) {
  return useQuery({ queryKey: spaceKeys.detail(spaceId ?? ""), queryFn: () => api.getSpace(spaceId as string), enabled: Boolean(spaceId) });
}

function useRefreshSpaces(projectId: string) {
  const qc = useQueryClient();
  return (spaceId?: string) => {
    void qc.invalidateQueries({ queryKey: spaceKeys.spacesRoot(projectId) });
    if (spaceId) {
      void qc.invalidateQueries({ queryKey: spaceKeys.detail(spaceId) });
      void qc.invalidateQueries({ queryKey: [...K, "finish-preview", spaceId] });
    }
  };
}

export function useCreateSpace(projectId: string) {
  const refresh = useRefreshSpaces(projectId);
  return useMutation({ mutationFn: (b: SpaceCreateRequest) => api.createSpace(projectId, b), onSuccess: () => refresh() });
}

export function useUpdateSpace(projectId: string) {
  const refresh = useRefreshSpaces(projectId);
  return useMutation({ mutationFn: ({ spaceId, payload }: { spaceId: string; payload: SpaceUpdateRequest }) => api.updateSpace(spaceId, payload), onSuccess: (s) => refresh(s.id) });
}

export function useDeleteSpace(projectId: string) {
  const refresh = useRefreshSpaces(projectId);
  return useMutation({ mutationFn: (spaceId: string) => api.deleteSpace(spaceId), onSuccess: (_d, spaceId) => refresh(spaceId) });
}

export function useSetSpaceBoundaries(projectId: string) {
  const refresh = useRefreshSpaces(projectId);
  return useMutation({ mutationFn: ({ spaceId, elementIds }: { spaceId: string; elementIds: string[] }) => api.setBoundaries(spaceId, elementIds), onSuccess: (_d, v) => refresh(v.spaceId) });
}

export function useUpsertSpaceFinish(projectId: string) {
  const refresh = useRefreshSpaces(projectId);
  return useMutation({ mutationFn: ({ spaceId, payload }: { spaceId: string; payload: SpaceFinishCreateRequest }) => api.upsertFinish(spaceId, payload), onSuccess: (_d, v) => refresh(v.spaceId) });
}

export function useDeleteSpaceFinish(projectId: string) {
  const refresh = useRefreshSpaces(projectId);
  return useMutation({ mutationFn: ({ finishId }: { finishId: string; spaceId: string }) => api.deleteFinish(finishId), onSuccess: (_d, v) => refresh(v.spaceId) });
}

export function useFinishPreview(spaceId: string | undefined, ruleSetCode: string, enabled: boolean) {
  return useQuery({
    queryKey: spaceKeys.preview(spaceId ?? "", ruleSetCode),
    queryFn: () => api.previewFinishes(spaceId as string, ruleSetCode || undefined),
    enabled: Boolean(spaceId) && enabled,
    retry: false,
  });
}

export function useScheduleImports(projectId: string, status?: string) {
  return useQuery({ queryKey: spaceKeys.imports(projectId, status), queryFn: () => api.listImports(projectId, status), enabled: Boolean(projectId) });
}

export function useScheduleImportDetail(importId: string | undefined) {
  return useQuery({ queryKey: spaceKeys.importDetail(importId ?? ""), queryFn: () => api.getImport(importId as string), enabled: Boolean(importId) });
}

export function useImportScheduleFile(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, kind, notes }: { file: File; kind: ScheduleKind; notes?: string | null }) => api.importFile(projectId, file, kind, notes),
    onSuccess: () => void qc.invalidateQueries({ queryKey: spaceKeys.importsRoot(projectId) }),
  });
}

export function useImportSchedulePdf(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: ScheduleFromPdfRequest) => api.importFromPdf(projectId, b),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: spaceKeys.importsRoot(projectId) });
      void qc.invalidateQueries({ queryKey: [...K, "quota"] });
    },
  });
}

export function useCreateManualSchedule(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: ScheduleManualCreateRequest) => api.createManualImport(projectId, b),
    onSuccess: () => void qc.invalidateQueries({ queryKey: spaceKeys.importsRoot(projectId) }),
  });
}

function useRefreshImport(importId: string) {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: spaceKeys.importDetail(importId) });
}

export function useAddScheduleRow(importId: string) {
  const refresh = useRefreshImport(importId);
  return useMutation({ mutationFn: (b: ScheduleRowCreateRequest) => api.addRow(importId, b), onSuccess: refresh });
}

export function useUpdateScheduleRow(importId: string) {
  const refresh = useRefreshImport(importId);
  return useMutation({ mutationFn: ({ rowId, payload }: { rowId: string; payload: ScheduleRowUpdateRequest }) => api.updateRow(rowId, payload), onSuccess: refresh });
}

export function useBulkReviewScheduleRows(importId: string) {
  const refresh = useRefreshImport(importId);
  return useMutation({ mutationFn: ({ rowIds, decision }: { rowIds: string[]; decision: RowDecision }) => api.bulkReview(importId, rowIds, decision), onSuccess: refresh });
}

export function useConfirmScheduleImport(projectId: string, importId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rejectPending: boolean) => api.confirmImport(importId, rejectPending),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: spaceKeys.importDetail(importId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.importsRoot(projectId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.spacesRoot(projectId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.detailRoot() });
    },
  });
}

export function useRejectScheduleImport(projectId: string, importId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (note: string | null) => api.rejectImport(importId, note),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: spaceKeys.importDetail(importId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.importsRoot(projectId) });
    },
  });
}

export function useArchiveScheduleImport(projectId: string, importId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.archiveImport(importId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: spaceKeys.importDetail(importId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.importsRoot(projectId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.spacesRoot(projectId) });
      void qc.invalidateQueries({ queryKey: spaceKeys.detailRoot() });
    },
  });
}

export function useRematchScheduleImport(importId: string) {
  const refresh = useRefreshImport(importId);
  return useMutation({ mutationFn: () => api.rematchImport(importId), onSuccess: refresh });
}
