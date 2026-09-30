import { authenticatedRequest } from "./client";
import type {ChangeOrder, ChangeOrderCreatePayload, ChangeOrderDetail, ProjectChangeOrderSummary,
} from "./types";

const body = (value: unknown) => JSON.stringify(value);

export function listChangeOrders(projectId: string): Promise<ChangeOrderDetail[]> {
  return authenticatedRequest<ChangeOrderDetail[]>(
    `/change-orders?project_id=${encodeURIComponent(projectId)}`,
  );
}

export function getChangeOrder(
  changeOrderId: string,
): Promise<ChangeOrderDetail> {
  return authenticatedRequest<ChangeOrderDetail>(
    `/change-orders/${encodeURIComponent(changeOrderId)}`,
  );
}

export function getProjectChangeOrderSummary(
  projectId: string,
): Promise<ProjectChangeOrderSummary> {
  return authenticatedRequest<ProjectChangeOrderSummary>(
    `/change-orders/projects/${encodeURIComponent(projectId)}/summary`,
  );
}

export function createChangeOrder(
  payload: ChangeOrderCreatePayload,
): Promise<ChangeOrderDetail> {
  return authenticatedRequest<ChangeOrderDetail>("/change-orders", {
    method: "POST",
    body: body(payload),
  });
}

export function approveChangeOrder(
  changeOrderId: string,
  version: number,
): Promise<ChangeOrder> {
  return authenticatedRequest<ChangeOrder>(
    `/change-orders/${encodeURIComponent(changeOrderId)}/approve`,
    { method: "POST", body: body({ version }) },
  );
}

export function rejectChangeOrder(
  changeOrderId: string,
  version: number,
  reason: string,
): Promise<ChangeOrder> {
  return authenticatedRequest<ChangeOrder>(
    `/change-orders/${encodeURIComponent(changeOrderId)}/reject`,
    { method: "POST", body: body({ version, reason }) },
  );
}

export function cancelChangeOrder(
  changeOrderId: string,
  version: number,
): Promise<ChangeOrder> {
  return authenticatedRequest<ChangeOrder>(
    `/change-orders/${encodeURIComponent(changeOrderId)}/cancel`,
    { method: "POST", body: body({ version }) },
  );
}