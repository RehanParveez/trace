import { apiClient } from "../../../shared/api/client";
import type {RecordCollectionRequest, RunningBill, RunningBillCollection, RunningBillCreateRequest, RunningBillDetail,
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

  async cancel(billId: string, version: number, reason?: string): Promise<RunningBill> {
    const response = await apiClient.post<RunningBill>(
      `/running-bills/${billId}/cancel`,
      { version, reason: reason ?? null },
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

  async recordCollection(billId: string, payload: RecordCollectionRequest): Promise<RunningBill> {
    const response = await apiClient.post<RunningBill>(`/running-bills/${billId}/record-collection`, payload);
    return response.data;
  },

  async listCollections(billId: string): Promise<RunningBillCollection[]> {
    const response = await apiClient.get<RunningBillCollection[]>(`/running-bills/${billId}/collections`);
    return response.data;
  },

  async voidCollection(billId: string, collectionId: string, reason: string): Promise<RunningBill> {
    const response = await apiClient.post<RunningBill>(
      `/running-bills/${billId}/collections/${collectionId}/void`,
      { reason },
    );
    return response.data;
  },
};