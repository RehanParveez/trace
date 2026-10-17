import { apiClient } from "../../../../shared/api/client";
import type { BillClasses, BillCompareResult } from "../types/billCompare.types";

const BASE = "/drawings-boq";

export const steelCompareApi = {
  async compare(runId: string, file: File, tolerancePct: number, classes: BillClasses): Promise<BillCompareResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("tolerance_pct", String(tolerancePct));
    form.append("classes", JSON.stringify(classes));
    return (await apiClient.post<BillCompareResult>(`${BASE}/calculation-runs/${runId}/compare-steel`, form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
  async exportXlsx(result: BillCompareResult): Promise<Blob> {
    return (await apiClient.post<Blob>(`${BASE}/compare-bill/export`, result, { responseType: "blob" })).data;
  },
};
