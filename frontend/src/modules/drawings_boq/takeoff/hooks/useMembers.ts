import { useQuery } from "@tanstack/react-query";
import { membersApi } from "../api/members.api";
import { takeoffKeys } from "./useTakeoff";

export const memberKeys = { list: (drawingId: string) => [...takeoffKeys.floorSources(drawingId), "members"] as const };

export function useMembers(drawingId: string | undefined, enabled = true) {
  return useQuery({ queryKey: memberKeys.list(drawingId ?? ""), queryFn: () => membersApi.get(drawingId as string), enabled: Boolean(drawingId) && enabled });
}
