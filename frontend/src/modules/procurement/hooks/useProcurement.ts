import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { procurementApi } from "../api/procurement.api";
import type {ProcurementDeliveryCreateRequest, ProcurementCreateRequest, ProcurementListParams, ProcurementStatusUpdateRequest,
} from "../types/procurement.types";

export const procurementKeys = {
  all: ["procurement"] as const,
  list: (params: ProcurementListParams) => [...procurementKeys.all, "list", params] as const,
  organizationSummary: () => [...procurementKeys.all, "organization-summary"] as const,
  statusSummary: (projectId?: string) => [...procurementKeys.all, "status-summary", projectId] as const,  // ← ADD this line
};

export function useProcurementRequests(params: ProcurementListParams = {}, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: procurementKeys.list(params),
    queryFn: () => procurementApi.listRequests(params),
    enabled: options?.enabled,
  });
}

function invalidateProcurementLists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({
    queryKey: procurementKeys.all,
    predicate: (query) => query.queryKey[1] === "list" || query.queryKey[1] === "status-summary",
  });
}

export function useCreateProcurementRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProcurementCreateRequest) => procurementApi.createRequest(payload),
    onSuccess: () => invalidateProcurementLists(queryClient),
  });
}

export function useUpdateProcurementStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, payload }: { requestId: string; payload: ProcurementStatusUpdateRequest }) =>
      procurementApi.updateStatus(requestId, payload),
    onSuccess: () => invalidateProcurementLists(queryClient),
  });
}

function invalidateAfterDelivery(queryClient: ReturnType<typeof useQueryClient>) {
  invalidateProcurementLists(queryClient);
  void queryClient.invalidateQueries({ queryKey: [...procurementKeys.all, "deliveries"] });
  void queryClient.invalidateQueries({ queryKey: ["material-stock"] });
  void queryClient.invalidateQueries({ queryKey: ["budgets", "status"] });
}

export function useProcurementDeliveries(requestId: string | undefined) {
  return useQuery({
    queryKey: [...procurementKeys.all, "deliveries", requestId ?? ""] as const,
    queryFn: () => procurementApi.listDeliveries(requestId as string),
    enabled: Boolean(requestId),
  });
}

export function useRecordDelivery(requestId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProcurementDeliveryCreateRequest) => procurementApi.recordDelivery(requestId, payload),
    onSuccess: () => invalidateAfterDelivery(queryClient),
  });
}

export function useVoidDelivery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deliveryId, reason }: { deliveryId: string; reason: string }) => procurementApi.voidDelivery(deliveryId, reason),
    onSuccess: () => invalidateAfterDelivery(queryClient),
  });
}

export function useProcurementOrganizationSummary(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: procurementKeys.organizationSummary(),
    queryFn: procurementApi.getOrganizationSummary,
    enabled: options?.enabled,
  });
}

export function useProcurementStatusSummary(projectId?: string) {
  return useQuery({
    queryKey: procurementKeys.statusSummary(projectId),
    queryFn: () => procurementApi.getStatusSummary({ projectId }),
  });
}