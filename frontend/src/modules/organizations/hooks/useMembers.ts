import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { organizationsApi } from "../api/organizations.api";
import type {MemberRoleUpdateRequest, MemberStatusUpdateRequest,
} from "../types/organization.types";

export const memberKeys = {
  all: [
    "organizations",
    "members",
  ] as const,

  list: (
    skip: number,
    limit: number,
  ) =>
    [
      ...memberKeys.all,
      "list",
      skip,
      limit,
    ] as const,

  detail: (userId: string) =>
    [
      ...memberKeys.all,
      "detail",
      userId,
    ] as const,
};

export function useMembers(
  skip = 0,
  limit = 100,
) {
  return useQuery({
    queryKey: memberKeys.list(
      skip,
      limit,
    ),

    queryFn: () =>
      organizationsApi.listMembers(
        skip,
        limit,
      ),
  });
}

export function useMember(
  userId?: string,
) {
  return useQuery({
    queryKey: memberKeys.detail(
      userId ?? "",
    ),

    queryFn: () =>
      organizationsApi.getMember(
        userId!,
      ),

    enabled: Boolean(userId),
  });
}

export function useUpdateMemberRole() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: MemberRoleUpdateRequest;
    }) =>
      organizationsApi.updateMemberRole(
        userId,
        payload,
      ),

    onSuccess: (member) => {
      queryClient.setQueryData(
        memberKeys.detail(member.id),
        member,
      );

      void queryClient.invalidateQueries({
        queryKey: memberKeys.all,
      });
    },
  });
}

export function useUpdateMemberStatus() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: MemberStatusUpdateRequest;
    }) =>
      organizationsApi.updateMemberStatus(
        userId,
        payload,
      ),

    onSuccess: (member) => {
      queryClient.setQueryData(
        memberKeys.detail(member.id),
        member,
      );

      void queryClient.invalidateQueries({
        queryKey: memberKeys.all,
      });
    },
  });
}