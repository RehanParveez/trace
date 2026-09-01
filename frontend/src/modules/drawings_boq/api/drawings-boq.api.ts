import { apiClient } from "../../../shared/api/client";
import type {BOQCustomItemCreateRequest, BOQItem, BOQItemUpdateRequest, BOQSummary, BOQVersion, BOQVersionUpdateRequest, Drawing, DrawingElement, LabourRate,
  LabourRateCreateRequest, LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryEntry, MaterialLibraryUpdateRequest,
} from "../types/drawings-boq.types";

export const drawingsBoqApi = {
  async uploadDrawing(projectId: string, file: File, idempotencyKey: string): Promise<Drawing> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post<Drawing>(
      `/drawings-boq/projects/${projectId}/drawings`,
      formData,
      { headers: { "Idempotency-Key": idempotencyKey } },
    );

    return response.data;
  },

  async listDrawings(projectId: string): Promise<Drawing[]> {
    const response = await apiClient.get<Drawing[]>(`/drawings-boq/projects/${projectId}/drawings`);
    return response.data;
  },

  async listDrawingElements(drawingId: string): Promise<DrawingElement[]> {
    const response = await apiClient.get<DrawingElement[]>(`/drawings-boq/drawings/${drawingId}/elements`);
    return response.data;
  },

  async listBOQVersions(projectId: string): Promise<BOQVersion[]> {
    const response = await apiClient.get<BOQVersion[]>(`/drawings-boq/projects/${projectId}/boq-versions`);
    return response.data;
  },

  async listBOQItems(boqVersionId: string): Promise<BOQItem[]> {
    const response = await apiClient.get<BOQItem[]>(`/drawings-boq/boq-versions/${boqVersionId}/items`);
    return response.data;
  },

  async updateBOQItem(itemId: string, payload: BOQItemUpdateRequest): Promise<BOQItem> {
    const response = await apiClient.patch<BOQItem>(`/drawings-boq/boq-items/${itemId}`, payload);
    return response.data;
  },

  async approveBOQItem(itemId: string): Promise<BOQItem> {
    const response = await apiClient.post<BOQItem>(`/drawings-boq/boq-items/${itemId}/approve`);
    return response.data;
  },

  async listMaterialLibrary(): Promise<MaterialLibraryEntry[]> {
    const response = await apiClient.get<MaterialLibraryEntry[]>("/drawings-boq/material-library");
    return response.data;
  },

    async createMaterialLibraryEntry(payload: MaterialLibraryCreateRequest): Promise<MaterialLibraryEntry> {
    const response = await apiClient.post<MaterialLibraryEntry>("/drawings-boq/material-library", payload);
    return response.data;
  },

  async updateMaterialLibraryEntry(entryId: string, payload: MaterialLibraryUpdateRequest): Promise<MaterialLibraryEntry> {
    const response = await apiClient.patch<MaterialLibraryEntry>(`/drawings-boq/material-library/${entryId}`, payload);
    return response.data;
  },

  async listLabourRates(): Promise<LabourRate[]> {
    const response = await apiClient.get<LabourRate[]>("/drawings-boq/labour-rates");
    return response.data;
  },

  async createLabourRate(payload: LabourRateCreateRequest): Promise<LabourRate> {
    const response = await apiClient.post<LabourRate>("/drawings-boq/labour-rates", payload);
    return response.data;
  },

  async updateLabourRate(rateId: string, payload: LabourRateUpdateRequest): Promise<LabourRate> {
    const response = await apiClient.patch<LabourRate>(`/drawings-boq/labour-rates/${rateId}`, payload);
    return response.data;
  },

  async addCustomBOQItem(boqVersionId: string, payload: BOQCustomItemCreateRequest): Promise<BOQItem> {
    const response = await apiClient.post<BOQItem>(`/drawings-boq/boq-versions/${boqVersionId}/items`, payload);
    return response.data;
  },

  async updateBOQVersion(boqVersionId: string, payload: BOQVersionUpdateRequest): Promise<BOQVersion> {
    const response = await apiClient.patch<BOQVersion>(`/drawings-boq/boq-versions/${boqVersionId}`, payload);
    return response.data;
  },

  async generateLabourItems(boqVersionId: string): Promise<BOQItem[]> {
    const response = await apiClient.post<BOQItem[]>(`/drawings-boq/boq-versions/${boqVersionId}/labour/generate`);
    return response.data;
  },

  async getBOQSummary(boqVersionId: string): Promise<BOQSummary> {
    const response = await apiClient.get<BOQSummary>(`/drawings-boq/boq-versions/${boqVersionId}/summary`);
    return response.data;
  },

  async exportBOQPdf(boqVersionId: string): Promise<Blob> {
    const response = await apiClient.get(`/drawings-boq/boq-versions/${boqVersionId}/export/pdf`, {
      responseType: "blob",
    });
    return response.data;
  },

  async exportBOQXlsx(boqVersionId: string): Promise<Blob> {
    const response = await apiClient.get(`/drawings-boq/boq-versions/${boqVersionId}/export/xlsx`, {
      responseType: "blob",
    });
    return response.data;
  },
};