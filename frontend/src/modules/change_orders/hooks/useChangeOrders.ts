import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { changeOrdersApi } from "../api/change-orders.api";
import type { ChangeOrderType } from "../types/change-order.types";

export const changeOrderKeys = {
  all: ["change-orders"] as const,
  list: (projectId: string) => [...changeOrderKeys.all, "list", projectId] as const,
  detail: (id: string) => [...changeOrderKeys.all, "detail", id] as const,
  summary: (projectId: string) => [...changeOrderKeys.all, "summary", projectId] as const,
};

export function useChangeOrders(projectId: string) {
  return useQuery({ queryKey: changeOrderKeys.list(projectId), queryFn: () => changeOrdersApi.list(projectId), enabled: Boolean(projectId) });
}

export function useChangeOrder(id: string | undefined) {
  return useQuery({ queryKey: changeOrderKeys.detail(id ?? ""), queryFn: () => changeOrdersApi.get(id as string), enabled: Boolean(id) });
}

export function useChangeOrderSummary(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: changeOrderKeys.summary(projectId),
    queryFn: () => changeOrdersApi.getProjectSummary(projectId),
    enabled: Boolean(projectId) && (options?.enabled ?? true),
  });
}

export function useCreateChangeOrder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<Parameters<typeof changeOrdersApi.create>[0], "project_id">) =>
      changeOrdersApi.create({ ...payload, project_id: projectId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: changeOrderKeys.list(projectId) });
      void qc.invalidateQueries({ queryKey: changeOrderKeys.summary(projectId) });
    },
  });
}

function invalidateAfterStatusChange(qc: ReturnType<typeof useQueryClient>, projectId: string, changeOrderId: string) {
  void qc.invalidateQueries({ queryKey: changeOrderKeys.list(projectId) });
  void qc.invalidateQueries({ queryKey: changeOrderKeys.detail(changeOrderId) });
  void qc.invalidateQueries({ queryKey: changeOrderKeys.summary(projectId) });
}

export function useApproveChangeOrder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) => changeOrdersApi.approve(id, version),
    onSuccess: (co) => invalidateAfterStatusChange(qc, projectId, co.id),
  });
}

export function useRejectChangeOrder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, version, reason }: { id: string; version: number; reason: string }) =>
      changeOrdersApi.reject(id, version, reason),
    onSuccess: (co) => invalidateAfterStatusChange(qc, projectId, co.id),
  });
}

export function useCancelChangeOrder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) => changeOrdersApi.cancel(id, version),
    onSuccess: (co) => invalidateAfterStatusChange(qc, projectId, co.id),
  });
}