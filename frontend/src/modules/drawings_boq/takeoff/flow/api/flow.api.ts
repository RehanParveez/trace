import { apiClient } from "../../../../../shared/api/client";
import type { ExportKind, FlowBoq, FlowStatus, RateBookOption, SeenStep } from "../types/flow.types";

const BASE = "/drawings-boq";
const flowUrl = (projectId: string) => `${BASE}/projects/${projectId}/flow`;

export const flowApi = {
  async status(projectId: string, profile: string | null): Promise<FlowStatus> {
    return (await apiClient.get<FlowStatus>(flowUrl(projectId), { params: profile ? { profile } : undefined })).data;
  },
  async boq(projectId: string, profile: string | null, rateBookId: string | null): Promise<FlowBoq> {
    const params: Record<string, string> = {};
    if (profile) params.profile = profile;
    if (rateBookId) params.rate_book_id = rateBookId;
    return (await apiClient.get<FlowBoq>(`${flowUrl(projectId)}/boq`, { params })).data;
  },
  async seen(projectId: string, step: SeenStep): Promise<void> {
    await apiClient.post(`${flowUrl(projectId)}/seen`, { step });
  },
  async upload(projectId: string, file: File): Promise<void> {
    const body = new FormData();
    body.append("file", file);
    await apiClient.post(`${BASE}/projects/${projectId}/drawings`, body, { headers: { "Idempotency-Key": crypto.randomUUID() } });
  },
  async startRead(projectId: string): Promise<void> {
    await apiClient.post(`${BASE}/projects/${projectId}/first-run`);
  },
  async startQuantities(projectId: string): Promise<void> {
    await apiClient.post(`${BASE}/projects/${projectId}/calculation-runs`, {});
  },
  async rateBooks(): Promise<RateBookOption[]> {
    return (await apiClient.get<RateBookOption[]>(`${BASE}/rate-books`, { params: { status: "ACTIVE" } })).data;
  },
  async download(projectId: string, kind: ExportKind, profile: string | null, rateBookId: string | null): Promise<{ blob: Blob; name: string }> {
    const params: Record<string, string> = {};
    if (profile) params.profile = profile;
    if (rateBookId) params.rate_book_id = rateBookId;
    const res = await apiClient.get<Blob>(`${flowUrl(projectId)}/export/${kind}`, { params, responseType: "blob" });
    const named = /filename="([^"]+)"/.exec(String(res.headers["content-disposition"] ?? ""));
    return { blob: res.data, name: named ? named[1] : `${kind}-${projectId}` };
  },
};
