import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiShadowApi } from "../api/aiShadow.api";
import type { ShadowMode } from "../types/aiShadow.types";

export const aiShadowKey = (drawingId: string) => ["takeoff", "ai-shadow", drawingId] as const;

export function useAiShadow(drawingId: string | undefined) {
  return useQuery({
    queryKey: aiShadowKey(drawingId ?? ""),
    queryFn: () => aiShadowApi.summary(drawingId as string),
    enabled: Boolean(drawingId),
    staleTime: 30_000,
    retry: false,
  });
}

export function useRunAiShadow(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { mode: ShadowMode; limit?: number; force?: boolean }) => aiShadowApi.run(drawingId as string, body),
    onSuccess: () => {
      if (drawingId) void qc.invalidateQueries({ queryKey: aiShadowKey(drawingId) });
    },
  });
}
