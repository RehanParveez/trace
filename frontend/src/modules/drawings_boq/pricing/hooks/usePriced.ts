import { useQuery } from "@tanstack/react-query";
import { pricedApi } from "../api/priced.api";

export const pricedKeys = {
  all: ["drawings-boq", "priced"] as const,
  view: (projectId: string, profile: string, rateBookId: string) => ["drawings-boq", "priced", projectId, profile, rateBookId] as const,
};

export function usePriced(projectId: string | undefined, profile: string, rateBookId: string) {
  return useQuery({
    queryKey: pricedKeys.view(projectId ?? "", profile, rateBookId),
    queryFn: () => pricedApi.get(projectId as string, profile, rateBookId),
    enabled: Boolean(projectId),
  });
}
