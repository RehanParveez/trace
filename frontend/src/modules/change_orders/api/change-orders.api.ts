import { apiClient } from "../../../shared/api/client";
import type {ChangeOrderDetail, ChangeOrderType, ProjectChangeOrderSummary,
} from "../types/change-order.types";

interface LineItemInput {
  description: string;
  unit: string;
  boq_item_id?: string | null;
  quantity: number;
  unit_rate?: number | null;
}

export const changeOrdersApi = {
  async list(projectId: string): Promise<ChangeOrderDetail[]> {
    return (await apiClient.get<ChangeOrderDetail[]>("/change-orders", { params: { project_id: projectId } })).data;
  },
  async get(changeOrderId: string): Promise<ChangeOrderDetail> {
    return (await apiClient.get<ChangeOrderDetail>(`/change-orders/${changeOrderId}`)).data;
  },
  async create(payload: {
    project_id: string; boq_version_id: string; change_type: ChangeOrderType;
    title: string; description?: string | null; client_reference?: string | null;
    line_items: LineItemInput[];
  }): Promise<ChangeOrderDetail> {
    return (await apiClient.post<ChangeOrderDetail>("/change-orders", payload)).data;
  },
  async approve(changeOrderId: string, version: number): Promise<ChangeOrderDetail> {
    return (await apiClient.post<ChangeOrderDetail>(`/change-orders/${changeOrderId}/approve`, { version })).data;
  },
  async reject(changeOrderId: string, version: number, reason: string): Promise<ChangeOrderDetail> {
    return (await apiClient.post<ChangeOrderDetail>(`/change-orders/${changeOrderId}/reject`, { version, reason })).data;
  },
  async cancel(changeOrderId: string, version: number): Promise<ChangeOrderDetail> {
    return (await apiClient.post<ChangeOrderDetail>(`/change-orders/${changeOrderId}/cancel`, { version })).data;
  },
  async getProjectSummary(projectId: string): Promise<ProjectChangeOrderSummary> {
    return (await apiClient.get<ProjectChangeOrderSummary>(`/change-orders/projects/${projectId}/summary`)).data;
  },
};