import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../../shared/api/client";
import type { QsProposedSet } from "../utils/qsProposed";
import { drawingsBoqKeys } from "./useDrawingsBoq";

export const qsProposedKeys = {
  all: [...drawingsBoqKeys.all, "qs-proposed"] as const,
};

export function useQsProposed() {
  return useQuery({
    queryKey: qsProposedKeys.all,
    queryFn: async (): Promise<QsProposedSet | null> => {
      const response = await apiClient.get<{ proposed?: QsProposedSet }>("/drawings-boq/qs-answers");
      return response.data.proposed ?? null;
    },
    staleTime: 10 * 60 * 1000,
  });
}
