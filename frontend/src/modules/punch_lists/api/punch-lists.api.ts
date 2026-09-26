import { apiClient } from "../../../shared/api/client";
import type { PunchListDetail, PunchListPhotoPurpose, ProjectPunchListSummary } from "../types/punch-list.types";

export const punchListsApi = {
  async list(projectId: string): Promise<PunchListDetail[]> {
    return (await apiClient.get<PunchListDetail[]>("/punch-lists", { params: { project_id: projectId } })).data;
  },
  async get(punchListId: string): Promise<PunchListDetail> {
    return (await apiClient.get<PunchListDetail>(`/punch-lists/${punchListId}`)).data;
  },
  async create(payload: { project_id: string; title: string; inspection_date: string; notes?: string | null }): Promise<PunchListDetail> {
    return (await apiClient.post<PunchListDetail>("/punch-lists", payload)).data;
  },
  async close(punchListId: string): Promise<PunchListDetail> {
    return (await apiClient.post<PunchListDetail>(`/punch-lists/${punchListId}/close`, {})).data;
  },
  async addItem(punchListId: string, payload: {
    location: string; description: string; assigned_to_user_id?: string | null;
    assigned_to_subcontractor_id?: string | null; due_date?: string | null;
  }) {
    return (await apiClient.post(`/punch-lists/${punchListId}/items`, payload)).data;
  },
  async updateItem(itemId: string, payload: Record<string, unknown>) {
    return (await apiClient.patch(`/punch-lists/items/${itemId}`, payload)).data;
  },
  async addPhoto(itemId: string, sitePhotoId: string, purpose: PunchListPhotoPurpose) {
    return (await apiClient.post(`/punch-lists/items/${itemId}/photos`, { site_photo_id: sitePhotoId, photo_purpose: purpose })).data;
  },
  async removePhoto(linkId: string) {
    await apiClient.delete(`/punch-lists/photos/${linkId}`);
  },
  async getProjectSummary(projectId: string): Promise<ProjectPunchListSummary> {
    return (await apiClient.get<ProjectPunchListSummary>(`/punch-lists/projects/${projectId}/summary`)).data;
  },
};