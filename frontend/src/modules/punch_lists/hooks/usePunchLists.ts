import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { punchListsApi } from "../api/punch-lists.api";
import type { PunchListPhotoPurpose } from "../types/punch-list.types";

export const punchListKeys = {
  all: ["punch-lists"] as const,
  list: (projectId: string) => [...punchListKeys.all, "list", projectId] as const,
  detail: (id: string) => [...punchListKeys.all, "detail", id] as const,
  summary: (projectId: string) => [...punchListKeys.all, "summary", projectId] as const,
};

export function usePunchLists(projectId: string) {
  return useQuery({ queryKey: punchListKeys.list(projectId), queryFn: () => punchListsApi.list(projectId), enabled: Boolean(projectId) });
}

export function usePunchList(id: string | undefined) {
  return useQuery({ queryKey: punchListKeys.detail(id ?? ""), queryFn: () => punchListsApi.get(id as string), enabled: Boolean(id) });
}

export function usePunchListSummary(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: punchListKeys.summary(projectId),
    queryFn: () => punchListsApi.getProjectSummary(projectId),
    enabled: Boolean(projectId) && (options?.enabled ?? true),
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>, projectId: string, punchListId?: string) {
  void qc.invalidateQueries({ queryKey: punchListKeys.list(projectId) });
  void qc.invalidateQueries({ queryKey: punchListKeys.summary(projectId) });
  if (punchListId) void qc.invalidateQueries({ queryKey: punchListKeys.detail(punchListId) });
}

export function useCreatePunchList(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; inspection_date: string; notes?: string | null }) =>
      punchListsApi.create({ ...payload, project_id: projectId }),
    onSuccess: () => invalidateAll(qc, projectId),
  });
}

export function useClosePunchList(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (punchListId: string) => punchListsApi.close(punchListId),
    onSuccess: (pl) => invalidateAll(qc, projectId, pl.id),
  });
}

export function useAddPunchListItem(projectId: string, punchListId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof punchListsApi.addItem>[1]) => punchListsApi.addItem(punchListId, payload),
    onSuccess: () => invalidateAll(qc, projectId, punchListId),
  });
}

export function useUpdatePunchListItem(projectId: string, punchListId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: Record<string, unknown> }) => punchListsApi.updateItem(itemId, payload),
    onSuccess: () => invalidateAll(qc, projectId, punchListId),
  });
}

export function useAddPunchListPhoto(projectId: string, punchListId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, sitePhotoId, purpose }: { itemId: string; sitePhotoId: string; purpose: PunchListPhotoPurpose }) =>
      punchListsApi.addPhoto(itemId, sitePhotoId, purpose),
    onSuccess: () => invalidateAll(qc, projectId, punchListId),
  });
}

export function useRemovePunchListPhoto(projectId: string, punchListId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => punchListsApi.removePhoto(linkId),
    onSuccess: () => invalidateAll(qc, projectId, punchListId),
  });
}