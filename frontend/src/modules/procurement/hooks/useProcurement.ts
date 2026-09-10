import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { procurementApi } from "../api/procurement.api";
import type {ProcurementCreateRequest, ProcurementListParams, ProcurementStatusUpdateRequest,
} from "../types/procurement.types";

export const procurementKeys = {
  all: ["procurement"] as const,
  list: (params: ProcurementListParams) => [...procurementKeys.all, "list", params] as const,
};

export function useProcurementRequests(params: ProcurementListParams = {}) {
  return useQuery({
    queryKey: procurementKeys.list(params),
    queryFn: () => procurementApi.listRequests(params),
  });
}

function invalidateProcurementLists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({
    queryKey: procurementKeys.all,
    predicate: (query) => query.queryKey[1] === "list",
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