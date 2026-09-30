
import { authenticatedRequest } from "./client";
import type {ListSitePhotosFilters, PhotoTag, PhotoTagCreatePayload, ProjectPhotoThumbnail, SitePhoto, SitePhotoAssignProjectPayload, SitePhotoUpdatePayload, WhatsAppChannel, ChannelConnectPayload,
} from "./types";
import { File as ExpoFile } from "expo-file-system";

function buildPhotoQuery(filters: ListSitePhotosFilters = {}): string {
  const params = new URLSearchParams();

  if (filters.project_id) params.set("project_id", filters.project_id);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.photo_date_from) {
    params.set("photo_date_from", filters.photo_date_from);
  }
  if (filters.photo_date_to) {
    params.set("photo_date_to", filters.photo_date_to);
  }
  if (filters.unassigned_only === true) {
    params.set("unassigned_only", "true");
  }
  if (filters.skip != null) params.set("skip", String(filters.skip));
  if (filters.limit != null) {
    params.set("limit", String(Math.min(filters.limit, 100)));
  }

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function jsonBody(body: unknown): RequestInit {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export async function listSitePhotos(
  filters: ListSitePhotosFilters = {},
): Promise<SitePhoto[]> {
  return authenticatedRequest<SitePhoto[]>(
    `/whatsapp/photos${buildPhotoQuery(filters)}`,
  );
}

export async function getSitePhoto(
  photoId: string,
): Promise<SitePhoto> {
  return authenticatedRequest<SitePhoto>(
    `/whatsapp/photos/${photoId}`,
  );
}

export async function getLatestProjectPhotos(): Promise<
  ProjectPhotoThumbnail[]
> {
  return authenticatedRequest<ProjectPhotoThumbnail[]>(
    "/whatsapp/photos/latest-by-project",
  );
}

export async function updateSitePhoto(
  photoId: string,
  payload: SitePhotoUpdatePayload,
): Promise<SitePhoto> {
  return authenticatedRequest<SitePhoto>(
    `/whatsapp/photos/${photoId}`,
    {
      method: "PATCH",
      ...jsonBody(payload),
    },
  );
}

export async function assignSitePhotoToProject(
  photoId: string,
  projectId: string,
): Promise<SitePhoto> {
  const body: SitePhotoAssignProjectPayload = {
    project_id: projectId,
  };

  return authenticatedRequest<SitePhoto>(
    `/whatsapp/photos/${photoId}/assign-project`,
    {
      method: "POST",
      ...jsonBody(body),
    },
  );
}

export async function addPhotoTag(
  photoId: string,
  tag: string,
): Promise<PhotoTag> {
  const body: PhotoTagCreatePayload = { tag };

  return authenticatedRequest<PhotoTag>(
    `/whatsapp/photos/${photoId}/tags`,
    {
      method: "POST",
      ...jsonBody(body),
    },
  );
}

export async function removePhotoTag(
  photoId: string,
  tagId: string,
): Promise<void> {
  await authenticatedRequest<void>(
    `/whatsapp/photos/${photoId}/tags/${tagId}`,
    { method: "DELETE" },
  );
}

export async function getWhatsAppChannel(): Promise<WhatsAppChannel> {
  return authenticatedRequest<WhatsAppChannel>(
    "/whatsapp/channel",
  );
}

export async function connectWhatsAppChannel(
  payload: ChannelConnectPayload,
): Promise<WhatsAppChannel> {
  return authenticatedRequest<WhatsAppChannel>(
    "/whatsapp/channel",
    {
      method: "POST",
      ...jsonBody(payload),
    },
  );
}

export async function disconnectWhatsAppChannel(): Promise<void> {
  await authenticatedRequest<void>(
    "/whatsapp/channel",
    { method: "DELETE" },
  );
}

export async function uploadSitePhoto(
  projectId: string,
  asset: {
    uri: string;
    fileName?: string | null;
    mimeType?: string | null;
  },
): Promise<SitePhoto> {
  const formData = new FormData();
  formData.append("project_id", projectId);
  formData.append("file", new ExpoFile(asset.uri));

  return authenticatedRequest<SitePhoto>(
    "/whatsapp/photos/upload",
    {
      method: "POST",
      body: formData,
    },
  );
}