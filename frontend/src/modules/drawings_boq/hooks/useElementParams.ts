import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { elementParamsApi, type ElementParametersUpdate } from "../api/elementParams.api";
import { drawingsBoqKeys } from "./useDrawingsBoq";

export type { ElementParameters, ElementParametersUpdate } from "../api/elementParams.api";

export const elementParamsKeys = {
  project: (projectId: string) => [...drawingsBoqKeys.all, "element-parameters", projectId] as const,
};

export function useElementParameters(projectId: string | undefined) {
  return useQuery({
    queryKey: elementParamsKeys.project(projectId ?? ""),
    queryFn: () => elementParamsApi.get(projectId as string),
    enabled: Boolean(projectId),
  });
}

export function useSaveElementParameters(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (update: ElementParametersUpdate) => elementParamsApi.save(projectId as string, update),
    onSuccess: (saved) => {
      queryClient.setQueryData(elementParamsKeys.project(projectId ?? ""), saved);
    },
  });
}
