import { apiClient } from "../../../shared/api/client";
import type {Channel, ChannelConnectRequest, PhotoTag, PhotoTagCreateRequest, SitePhoto, SitePhotoAssignProjectRequest, SitePhotoListParams, SitePhotoUpdateRequest,
} from "../types/whatsapp.types";

export const whatsappApi = {
  async getChannel(): Promise<Channel> {
    const response = await apiClient.get<Channel>("/whatsapp/channel");
    return response.data;
  },

  async connectChannel(payload: ChannelConnectRequest): Promise<Channel> {
    const response = await apiClient.post<Channel>("/whatsapp/channel", payload);
    return response.data;
  },

  async disconnectChannel(): Promise<void> {
    await apiClient.delete("/whatsapp/channel");
  },

  async listPhotos(params: SitePhotoListParams = {}): Promise<SitePhoto[]> {
    const response = await apiClient.get<SitePhoto[]>("/whatsapp/photos", {
      params: {
        project_id: params.projectId,
        photo_date_from: params.photoDateFrom,
        photo_date_to: params.photoDateTo,
        tag: params.tag,
        unassigned_only: params.unassignedOnly,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
      },
    });
    return response.data;
  },

  async getPhoto(photoId: string): Promise<SitePhoto> {
    const response = await apiClient.get<SitePhoto>(`/whatsapp/photos/${photoId}`);
    return response.data;
  },

  async updatePhoto(photoId: string, payload: SitePhotoUpdateRequest): Promise<SitePhoto> {
    const response = await apiClient.patch<SitePhoto>(`/whatsapp/photos/${photoId}`, payload);
    return response.data;
  },

  async assignProject(photoId: string, payload: SitePhotoAssignProjectRequest): Promise<SitePhoto> {
    const response = await apiClient.post<SitePhoto>(`/whatsapp/photos/${photoId}/assign-project`, payload);
    return response.data;
  },

  async addTag(photoId: string, payload: PhotoTagCreateRequest): Promise<PhotoTag> {
    const response = await apiClient.post<PhotoTag>(`/whatsapp/photos/${photoId}/tags`, payload);
    return response.data;
  },

  async removeTag(photoId: string, tagId: string): Promise<void> {
    await apiClient.delete(`/whatsapp/photos/${photoId}/tags/${tagId}`);
  },
};