import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { measurementParamsApi, type MeasurementParametersUpdate } from "../api/measurementParams.api";
import { drawingsBoqKeys } from "./useDrawingsBoq";

export type { MeasurementParameters, MeasurementParametersUpdate } from "../api/measurementParams.api";

export const measurementParamsKeys = {
  project: (projectId: string) => [...drawingsBoqKeys.all, "measurement-parameters", projectId] as const,
};

export function useMeasurementParameters(projectId: string | undefined) {
  return useQuery({
    queryKey: measurementParamsKeys.project(projectId ?? ""),
    queryFn: () => measurementParamsApi.get(projectId as string),
    enabled: Boolean(projectId),
  });
}

export function useSaveMeasurementParameters(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: MeasurementParametersUpdate) => measurementParamsApi.save(projectId as string, values),
    onSuccess: (saved) => {
      queryClient.setQueryData(measurementParamsKeys.project(projectId ?? ""), saved);
    },
  });
}