import { apiClient } from "../../../../shared/api/client";
import type { BillClasses, BillCompareResult } from "../types/billCompare.types";
import type { Reasonableness } from "../types/reasonableness.types";

const BASE = "/drawings-boq";

export const runCompareApi = {
  async compareBill(runId: string, file: File, tolerancePct: number, classes: BillClasses): Promise<BillCompareResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("tolerance_pct", String(tolerancePct));
    form.append("classes", JSON.stringify(classes));
    return (await apiClient.post<BillCompareResult>(`${BASE}/calculation-runs/${runId}/compare-bill`, form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
  async reasonableness(runId: string): Promise<Reasonableness> {
    return (await apiClient.get<Reasonableness>(`${BASE}/calculation-runs/${runId}/reasonableness`)).data;
  },
};
