import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { drawingsBoqKeys } from "../../../hooks/useDrawingsBoq";
import { steelBoqApi } from "../api/steelBoq.api";
import { steelKeys } from "./useSteelFigures";

export const steelBoqKeys = {
  root: ["steel-boq"] as const,
  version: (versionId: string) => ["steel-boq", versionId] as const,
};

export function useSteelBoq(versionId: string, enabled = true) {
  return useQuery({ queryKey: steelBoqKeys.version(versionId), queryFn: () => steelBoqApi.preview(versionId), enabled: Boolean(versionId) && enabled, retry: false });
}

export function useApplySteelBoq(versionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => steelBoqApi.apply(versionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: steelBoqKeys.root });
      void qc.invalidateQueries({ queryKey: steelKeys.root });
      void qc.invalidateQueries({ queryKey: drawingsBoqKeys.all });
    },
  });
}
