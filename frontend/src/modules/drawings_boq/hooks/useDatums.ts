import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { datumsApi, type DatumsUpdate } from "../api/datums.api";
import { drawingsBoqKeys } from "./useDrawingsBoq";

export type { DatumsResponse, DatumsUpdate, DatumView } from "../api/datums.api";

export const datumsKeys = {
  project: (projectId: string) => [...drawingsBoqKeys.all, "datums", projectId] as const,
};

export function useDatums(projectId: string | undefined) {
  return useQuery({
    queryKey: datumsKeys.project(projectId ?? ""),
    queryFn: () => datumsApi.get(projectId as string),
    enabled: Boolean(projectId),
  });
}

export function useSaveDatums(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: DatumsUpdate) => datumsApi.save(projectId as string, values),
    onSuccess: (saved) => {
      queryClient.setQueryData(datumsKeys.project(projectId ?? ""), saved);
    },
  });
}
