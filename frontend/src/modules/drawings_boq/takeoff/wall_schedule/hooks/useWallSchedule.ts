import { useQuery } from "@tanstack/react-query";
import { wallScheduleApi } from "../api/wallSchedule.api";
import { takeoffKeys } from "../../hooks/useTakeoff";

export const wallScheduleKey = (drawingId: string) => [...takeoffKeys.all, "wall-schedule", drawingId] as const;

export function useWallSchedule(drawingId: string | undefined, enabled: boolean) {
  return useQuery({ queryKey: wallScheduleKey(drawingId ?? ""), queryFn: () => wallScheduleApi.get(drawingId as string), enabled: Boolean(drawingId) && enabled });
}
