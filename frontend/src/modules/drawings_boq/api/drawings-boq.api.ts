import { apiClient } from "../../../shared/api/client";
import type {BOQItem, BOQItemUpdateRequest, BOQVersion, Drawing, DrawingElement, MaterialLibraryCreateRequest, MaterialLibraryEntry,
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
};