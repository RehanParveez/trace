import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { notesApi } from "../api/notes.api";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const notesKey = (drawingId: string, version: number) => [...takeoffKeys.all, "printed-notes", drawingId, version] as const;

export function useNotes(drawingId: string | undefined, version = 0, enabled = true) {
  return useQuery({
    queryKey: notesKey(drawingId ?? "", version),
    queryFn: () => notesApi.report(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
    placeholderData: keepPreviousData,
  });
}
