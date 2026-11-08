import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { takeoffKeys } from "../../hooks/useTakeoff";
import { reviewApi } from "../api/review.api";
import type { ReviewActionBody, ReviewActionResponse, ReviewResponse } from "../types/review.types";

export const reviewKey = (projectId: string, item: string | null) => [...takeoffKeys.all, "review", "project", projectId, item ?? ""] as const;

export function useReview(projectId: string | undefined, item: string | null = null) {
  return useQuery<ReviewResponse>({
    queryKey: reviewKey(projectId ?? "", item),
    queryFn: () => reviewApi.list(projectId as string, item),
    enabled: Boolean(projectId),
    placeholderData: keepPreviousData,
  });
}

export function useReviewAction(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation<ReviewActionResponse, unknown, { key: string; body: ReviewActionBody }>({
    mutationFn: ({ key, body }) => reviewApi.act(projectId as string, key, body),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: takeoffKeys.all });
    },
  });
}
