import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { runningBillsApi } from "../api/running-bills.api";
import type { RunningBillCreateRequest } from "../types/running-bill.types";

export const runningBillKeys = {
  all: ["running-bills"] as const,
  list: (projectId: string) =>
    [...runningBillKeys.all, "list", projectId] as const,
  detail: (billId: string) =>
    [...runningBillKeys.all, "detail", billId] as const,
};

export function useRunningBills(projectId: string | undefined) {
  return useQuery({
    queryKey: runningBillKeys.list(projectId ?? ""),
    queryFn: () => runningBillsApi.list(projectId as string),
    enabled: Boolean(projectId),
  });
}

export function useRunningBill(billId: string | undefined) {
  return useQuery({
    queryKey: runningBillKeys.detail(billId ?? ""),
    queryFn: () => runningBillsApi.get(billId as string),
    enabled: Boolean(billId),
  });
}

export function useCreateRunningBill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RunningBillCreateRequest) =>
      runningBillsApi.create(payload),
    onSuccess: (bill) =>
      void queryClient.invalidateQueries({
        queryKey: runningBillKeys.list(bill.project_id),
      }),
  });
}

export function useIssueRunningBill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      billId,
      version,
    }: {
      billId: string;
      version: number;
    }) => runningBillsApi.issue(billId, version),
    onSuccess: (bill) => {
      void queryClient.invalidateQueries({
        queryKey: runningBillKeys.list(bill.project_id),
      });
      void queryClient.invalidateQueries({
        queryKey: runningBillKeys.detail(bill.id),
      });
    },
  });
}

export function useCancelRunningBill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      billId,
      version,
    }: {
      billId: string;
      version: number;
    }) => runningBillsApi.cancel(billId, version),
    onSuccess: (bill) => {
      void queryClient.invalidateQueries({
        queryKey: runningBillKeys.list(bill.project_id),
      });
      void queryClient.invalidateQueries({
        queryKey: runningBillKeys.detail(bill.id),
      });
    },
  });
}