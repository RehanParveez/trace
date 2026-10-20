import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { expectedBoqApi } from "../api/expectedBoq.api";
import type { ExpectedTolerancesBody } from "../types/expectedBoq.types";

export const expectedBoqKeys = {
  list: (projectId: string) => ["expected-boq", "list", projectId] as const,
  detail: (projectId: string, expectedId: string) => ["expected-boq", "detail", projectId, expectedId] as const,
};

export function useExpectedBoqs(projectId: string | undefined) {
  return useQuery({ queryKey: expectedBoqKeys.list(projectId ?? ""), queryFn: () => expectedBoqApi.list(projectId as string), enabled: Boolean(projectId) });
}

export function useExpectedBoq(projectId: string | undefined, expectedId: string | undefined) {
  return useQuery({
    queryKey: expectedBoqKeys.detail(projectId ?? "", expectedId ?? ""),
    queryFn: () => expectedBoqApi.get(projectId as string, expectedId as string),
    enabled: Boolean(projectId && expectedId),
  });
}

export function useSaveExpectedBoq(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (v: { file: File; name: string }) => expectedBoqApi.save(projectId as string, v.file, v.name),
    onSuccess: (detail) => {
      queryClient.setQueryData(expectedBoqKeys.detail(projectId ?? "", detail.id), detail);
      void queryClient.invalidateQueries({ queryKey: expectedBoqKeys.list(projectId ?? "") });
    },
  });
}

export function useSetExpectedTolerances(projectId: string | undefined, expectedId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ExpectedTolerancesBody) => expectedBoqApi.setTolerances(projectId as string, expectedId as string, body),
    onSuccess: (detail) => {
      queryClient.setQueryData(expectedBoqKeys.detail(projectId ?? "", detail.id), detail);
      void queryClient.invalidateQueries({ queryKey: expectedBoqKeys.list(projectId ?? "") });
    },
  });
}

export function useRemoveExpectedBoq(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (expectedId: string) => expectedBoqApi.remove(projectId as string, expectedId),
    onSuccess: (items) => queryClient.setQueryData(expectedBoqKeys.list(projectId ?? ""), items),
  });
}

export function useDownloadExpectedBoq(projectId: string | undefined) {
  return useMutation({ mutationFn: (expectedId: string) => expectedBoqApi.download(projectId as string, expectedId) });
}

export function useCheckExpectedBoq(runId: string | undefined) {
  return useMutation({ mutationFn: (expectedId: string) => expectedBoqApi.check(runId as string, expectedId) });
}
