import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { integrityApi } from "../api/integrity.api";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const integrityKey = (drawingId: string, version: number) => [...takeoffKeys.all, "integrity", drawingId, version] as const;

export function useIntegrity(drawingId: string | undefined, version = 0, enabled = true) {
  return useQuery({
    queryKey: integrityKey(drawingId ?? "", version),
    queryFn: () => integrityApi.report(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
    placeholderData: keepPreviousData,
  });
}
