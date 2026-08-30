import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { drawingsBoqApi } from "../api/drawings-boq.api";
import { isDrawingInProgress } from "../utils/drawings-boq.utils";
import type { BOQItem, BOQItemUpdateRequest, Drawing, MaterialLibraryCreateRequest } from "../types/drawings-boq.types";

export const drawingsBoqKeys = {
  all: ["drawings-boq"] as const,
  drawings: (projectId: string) => [...drawingsBoqKeys.all, "drawings", projectId] as const,
  elements: (drawingId: string) => [...drawingsBoqKeys.all, "elements", drawingId] as const,
  boqVersions: (projectId: string) => [...drawingsBoqKeys.all, "boq-versions", projectId] as const,
  boqItems: (boqVersionId: string) => [...drawingsBoqKeys.all, "boq-items", boqVersionId] as const,
  materialLibrary: () => [...drawingsBoqKeys.all, "material-library"] as const,
};

export function useDrawings(projectId: string) {
  return useQuery({
    queryKey: drawingsBoqKeys.drawings(projectId),
    queryFn: () => drawingsBoqApi.listDrawings(projectId),
    enabled: Boolean(projectId),
    refetchInterval: (query) =>
      (query.state.data as Drawing[] | undefined)?.some((d) => isDrawingInProgress(d.status)) ? 4000 : false,
  });
}

export function useDrawingElements(drawingId: string | undefined) {
  return useQuery({
    queryKey: drawingsBoqKeys.elements(drawingId ?? ""),
    queryFn: () => drawingsBoqApi.listDrawingElements(drawingId!),
    enabled: Boolean(drawingId),
  });
}

export function useUploadDrawing(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, idempotencyKey }: { file: File; idempotencyKey: string }) =>
      drawingsBoqApi.uploadDrawing(projectId, file, idempotencyKey),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.drawings(projectId) }),
  });
}

export function useBOQVersions(projectId: string) {
  return useQuery({
    queryKey: drawingsBoqKeys.boqVersions(projectId),
    queryFn: () => drawingsBoqApi.listBOQVersions(projectId),
    enabled: Boolean(projectId),
  });
}

export function useBOQItems(boqVersionId: string | undefined) {
  return useQuery({
    queryKey: drawingsBoqKeys.boqItems(boqVersionId ?? ""),
    queryFn: () => drawingsBoqApi.listBOQItems(boqVersionId!),
    enabled: Boolean(boqVersionId),
  });
}

export function useUpdateBOQItem(boqVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: BOQItemUpdateRequest }) =>
      drawingsBoqApi.updateBOQItem(itemId, payload),
    onSuccess: (item) =>
      queryClient.setQueryData<BOQItem[]>(drawingsBoqKeys.boqItems(boqVersionId), (current) =>
        current?.map((existing) => (existing.id === item.id ? item : existing)),
      ),
  });
}

export function useApproveBOQItem(boqVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => drawingsBoqApi.approveBOQItem(itemId),
    onSuccess: (item) =>
      queryClient.setQueryData<BOQItem[]>(drawingsBoqKeys.boqItems(boqVersionId), (current) =>
        current?.map((existing) => (existing.id === item.id ? item : existing)),
      ),
  });
}

export function useMaterialLibrary() {
  return useQuery({ queryKey: drawingsBoqKeys.materialLibrary(), queryFn: drawingsBoqApi.listMaterialLibrary });
}

export function useCreateMaterialLibraryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: MaterialLibraryCreateRequest) => drawingsBoqApi.createMaterialLibraryEntry(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.materialLibrary() }),
  });
}