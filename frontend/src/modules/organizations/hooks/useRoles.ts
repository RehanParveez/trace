import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { organizationsApi } from "../api/organizations.api";
import type {RoleCreateRequest, RoleUpdateRequest,
} from "../types/organization.types";

export const roleKeys = {
  all: [
    "organizations",
    "roles",
  ] as const,

  list: () =>
    [
      ...roleKeys.all,
      "list",
    ] as const,

  detail: (roleId: string) =>
    [
      ...roleKeys.all,
      "detail",
      roleId,
    ] as const,
};

export function useRoles() {
  return useQuery({
    queryKey: roleKeys.list(),
    queryFn: organizationsApi.listRoles,
  });
}

export function useRole(
  roleId?: string,
) {
  return useQuery({
    queryKey: roleKeys.detail(
      roleId ?? "",
    ),

    queryFn: () =>
      organizationsApi.getRole(
        roleId!,
      ),

    enabled: Boolean(roleId),
  });
}

export function useCreateRole() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: (
      payload: RoleCreateRequest,
    ) =>
      organizationsApi.createRole(
        payload,
      ),

    onSuccess: (role) => {
      queryClient.setQueryData(
        roleKeys.detail(role.id),
        role,
      );

      void queryClient.invalidateQueries({
        queryKey: roleKeys.all,
      });
    },
  });
}

export function useUpdateRole() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: ({
      roleId,
      payload,
    }: {
      roleId: string;
      payload: RoleUpdateRequest;
    }) =>
      organizationsApi.updateRole(
        roleId,
        payload,
      ),

    onSuccess: (role) => {
      queryClient.setQueryData(
        roleKeys.detail(role.id),
        role,
      );

      void queryClient.invalidateQueries({
        queryKey: roleKeys.list(),
      });
    },
  });
}

export function useDeleteRole() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn:
      organizationsApi.deleteRole,

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: roleKeys.all,
      });
    },
  });
}