import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { whatsappApi } from "../api/whatsapp.api";
import type {ChannelConnectRequest, PhotoTagCreateRequest, SitePhoto, SitePhotoAssignProjectRequest, SitePhotoListParams, SitePhotoUpdateRequest,
} from "../types/whatsapp.types";

export const whatsappKeys = {
  all: ["whatsapp"] as const,
  channel: () => [...whatsappKeys.all, "channel"] as const,
  photos: (params: SitePhotoListParams) => [...whatsappKeys.all, "photos", params] as const,
  photo: (photoId: string) => [...whatsappKeys.all, "photo", photoId] as const,
};

export function useChannel() {
  return useQuery({
    queryKey: whatsappKeys.channel(),
    queryFn: whatsappApi.getChannel,
    retry: false,
  });
}

export function useConnectChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChannelConnectRequest) => whatsappApi.connectChannel(payload),
    onSuccess: (channel) => queryClient.setQueryData(whatsappKeys.channel(), channel),
  });
}

export function useDisconnectChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: whatsappApi.disconnectChannel,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: whatsappKeys.channel() }),
  });
}

export function useSitePhotos(params: SitePhotoListParams = {}) {
  return useQuery({
    queryKey: whatsappKeys.photos(params),
    queryFn: () => whatsappApi.listPhotos(params),
  });
}

export function useSitePhoto(photoId: string | undefined) {
  return useQuery({
    queryKey: whatsappKeys.photo(photoId ?? ""),
    queryFn: () => whatsappApi.getPhoto(photoId!),
    enabled: Boolean(photoId),
  });
}

function updatePhotoEverywhere(queryClient: ReturnType<typeof useQueryClient>, photo: SitePhoto) {
  queryClient.setQueryData(whatsappKeys.photo(photo.id), photo);
  void queryClient.invalidateQueries({ queryKey: whatsappKeys.all, predicate: (query) => query.queryKey[1] === "photos" });
}

export function useUpdateSitePhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ photoId, payload }: { photoId: string; payload: SitePhotoUpdateRequest }) =>
      whatsappApi.updatePhoto(photoId, payload),
    onSuccess: (photo) => updatePhotoEverywhere(queryClient, photo),
  });
}

export function useAssignProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ photoId, payload }: { photoId: string; payload: SitePhotoAssignProjectRequest }) =>
      whatsappApi.assignProject(photoId, payload),
    onSuccess: (photo) => updatePhotoEverywhere(queryClient, photo),
  });
}

export function useAddPhotoTag(photoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PhotoTagCreateRequest) => whatsappApi.addTag(photoId, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: whatsappKeys.photo(photoId) }),
  });
}

export function useRemovePhotoTag(photoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagId: string) => whatsappApi.removeTag(photoId, tagId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: whatsappKeys.photo(photoId) }),
  });
}