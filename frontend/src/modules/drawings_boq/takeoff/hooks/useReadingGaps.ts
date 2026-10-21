import { useQuery } from "@tanstack/react-query";
import { readingGapsApi } from "../api/readingGaps.api";
import type { TakeoffSheet } from "../types/takeoff.types";
import { takeoffKeys } from "./useTakeoff";

export const readingGapsKey = (sheetId: string) => [...takeoffKeys.all, "reading-gaps", sheetId] as const;

export function useReadingGaps(sheet: TakeoffSheet | undefined, enabled: boolean) {
  return useQuery({
    queryKey: readingGapsKey(sheet?.id ?? ""),
    queryFn: () => readingGapsApi.sheet(sheet!.id),
    enabled: Boolean(sheet && sheet.prep_status === "READY" && sheet.content_kind !== "RASTER") && enabled,
    retry: false,
  });
}
