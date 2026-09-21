import { apiClient } from "../../../shared/api/client";
import type {RunningBill, RunningBillCreateRequest, RunningBillDetail,
} from "../types/running-bill.types";

export const runningBillsApi = {
  async list(projectId: string): Promise<RunningBill[]> {
    const response = await apiClient.get<RunningBill[]>("/running-bills", {
      params: { project_id: projectId },
    });
    return response.data;
  },

  async get(billId: string): Promise<RunningBillDetail> {
    const response = await apiClient.get<RunningBillDetail>(
      `/running-bills/${billId}`,
    );
    return response.data;
  },

  async create(payload: RunningBillCreateRequest): Promise<RunningBillDetail> {
    const response = await apiClient.post<RunningBillDetail>(
      "/running-bills",
      payload,
    );
    return response.data;
  },

  async issue(billId: string, version: number): Promise<RunningBill> {
    const response = await apiClient.post<RunningBill>(
      `/running-bills/${billId}/issue`,
      { version },
    );
    return response.data;
  },

  async cancel(billId: string, version: number): Promise<RunningBill> {
    const response = await apiClient.post<RunningBill>(
      `/running-bills/${billId}/cancel`,
      { version },
    );
    return response.data;
  },

  async downloadPdf(billId: string): Promise<Blob> {
    const response = await apiClient.get(
      `/running-bills/${billId}/export/pdf`,
      { responseType: "blob" },
    );
    return response.data;
  },

  async downloadXlsx(billId: string): Promise<Blob> {
    const response = await apiClient.get(
      `/running-bills/${billId}/export/xlsx`,
      { responseType: "blob" },
    );
    return response.data;
  },
};