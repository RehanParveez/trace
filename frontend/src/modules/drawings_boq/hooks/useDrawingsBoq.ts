import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { drawingsBoqApi } from "../api/drawings-boq.api";
import { isDrawingInProgress, triggerBlobDownload } from "../utils/drawings-boq.utils";
import type {BOQCustomItemCreateRequest, BOQItem, BOQItemUpdateRequest, BOQVersion, BOQVersionUpdateRequest, Drawing, LabourRate, LabourRateCreateRequest,
  LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryEntry, MaterialLibraryUpdateRequest,
} from "../types/drawings-boq.types";

export const drawingsBoqKeys = {
  all: ["drawings-boq"] as const,
  drawings: (projectId: string) => [...drawingsBoqKeys.all, "drawings", projectId] as const,
  elements: (drawingId: string) => [...drawingsBoqKeys.all, "elements", drawingId] as const,
  boqVersions: (projectId: string) => [...drawingsBoqKeys.all, "boq-versions", projectId] as const,
  boqItems: (boqVersionId: string) => [...drawingsBoqKeys.all, "boq-items", boqVersionId] as const,
  boqSummary: (boqVersionId: string) => [...drawingsBoqKeys.all, "boq-summary", boqVersionId] as const,
  materialLibrary: () => [...drawingsBoqKeys.all, "material-library"] as const,
  labourRates: () => [...drawingsBoqKeys.all, "labour-rates"] as const,
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
    onSuccess: (item) => {
      queryClient.setQueryData<BOQItem[]>(drawingsBoqKeys.boqItems(boqVersionId), (current) =>
        current?.map((existing) => (existing.id === item.id ? item : existing)),
      );
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqSummary(boqVersionId) });
    },
  });
}

export function useApproveBOQItem(boqVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => drawingsBoqApi.approveBOQItem(itemId),
    onSuccess: (item) => {
      queryClient.setQueryData<BOQItem[]>(drawingsBoqKeys.boqItems(boqVersionId), (current) =>
        current?.map((existing) => (existing.id === item.id ? item : existing)),
      );
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqSummary(boqVersionId) });
    },
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

export function useUpdateMaterialLibraryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, payload }: { entryId: string; payload: MaterialLibraryUpdateRequest }) =>
      drawingsBoqApi.updateMaterialLibraryEntry(entryId, payload),
    onSuccess: (entry) =>
      queryClient.setQueryData<MaterialLibraryEntry[]>(drawingsBoqKeys.materialLibrary(), (current) =>
        current?.map((existing) => (existing.id === entry.id ? entry : existing)),
      ),
  });
}

export function useLabourRates() {
  return useQuery({ queryKey: drawingsBoqKeys.labourRates(), queryFn: drawingsBoqApi.listLabourRates });
}

export function useCreateLabourRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LabourRateCreateRequest) => drawingsBoqApi.createLabourRate(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.labourRates() }),
  });
}

export function useUpdateLabourRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ rateId, payload }: { rateId: string; payload: LabourRateUpdateRequest }) =>
      drawingsBoqApi.updateLabourRate(rateId, payload),
    onSuccess: (rate) =>
      queryClient.setQueryData<LabourRate[]>(drawingsBoqKeys.labourRates(), (current) =>
        current?.map((existing) => (existing.id === rate.id ? rate : existing)),
      ),
  });
}

export function useAddCustomBOQItem(boqVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BOQCustomItemCreateRequest) => drawingsBoqApi.addCustomBOQItem(boqVersionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqItems(boqVersionId) });
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqSummary(boqVersionId) });
    },
  });
}

export function useUpdateBOQVersion(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ boqVersionId, payload }: { boqVersionId: string; payload: BOQVersionUpdateRequest }) =>
      drawingsBoqApi.updateBOQVersion(boqVersionId, payload),
    onSuccess: (version) => {
      queryClient.setQueryData<BOQVersion[]>(drawingsBoqKeys.boqVersions(projectId), (current) =>
        current?.map((existing) => (existing.id === version.id ? version : existing)),
      );
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqSummary(version.id) });
    },
  });
}

export function useGenerateLabourItems(boqVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => drawingsBoqApi.generateLabourItems(boqVersionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqItems(boqVersionId) });
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.boqSummary(boqVersionId) });
    },
  });
}

export function useBOQSummary(boqVersionId: string | undefined) {
  return useQuery({
    queryKey: drawingsBoqKeys.boqSummary(boqVersionId ?? ""),
    queryFn: () => drawingsBoqApi.getBOQSummary(boqVersionId!),
    enabled: Boolean(boqVersionId),
  });
}

export function useExportBOQ(boqVersionId: string, label: string) {
  return useMutation({
    mutationFn: async (format: "pdf" | "xlsx") => {
      const blob = format === "pdf"
        ? await drawingsBoqApi.exportBOQPdf(boqVersionId)
        : await drawingsBoqApi.exportBOQXlsx(boqVersionId);
      triggerBlobDownload(blob, `BOQ-${label.replace(/\s+/g, "_")}.${format}`);
    },
  });
}