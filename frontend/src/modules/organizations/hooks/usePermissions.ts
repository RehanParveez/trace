import { useQuery } from "@tanstack/react-query";
import { organizationsApi } from "../api/organizations.api";

export const permissionKeys = {
  all: [
    "organizations",
    "permissions",
  ] as const,

  list: () =>
    [
      ...permissionKeys.all,
      "list",
    ] as const,
};

export function usePermissions() {
  return useQuery({
    queryKey: permissionKeys.list(),
    queryFn:
      organizationsApi.listPermissions,
  });
}