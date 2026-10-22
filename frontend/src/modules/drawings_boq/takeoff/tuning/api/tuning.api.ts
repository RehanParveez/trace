import { apiClient } from "../../../../../shared/api/client";
import type { DecideBody, DecideResult, PlanBody, SweepDetail, SweepList, TuningPlan, TuningRegistry } from "../types/tuning.types";

const BASE = "/drawings-boq";

export const tuningApi = {
  async registry(): Promise<TuningRegistry> {
    return (await apiClient.get<TuningRegistry>(`${BASE}/takeoff/tuning/registry`)).data;
  },
  async plan(drawingId: string, body: PlanBody): Promise<TuningPlan> {
    return (await apiClient.post<TuningPlan>(`${BASE}/drawings/${drawingId}/takeoff/tuning/plan`, body)).data;
  },
  async sweeps(drawingId: string): Promise<SweepList> {
    return (await apiClient.get<SweepList>(`${BASE}/drawings/${drawingId}/takeoff/tuning-sweeps`)).data;
  },
  async sweep(sweepId: string): Promise<SweepDetail> {
    return (await apiClient.get<SweepDetail>(`${BASE}/takeoff/tuning-sweeps/${sweepId}`)).data;
  },
  async decide(sweepId: string, body: DecideBody): Promise<DecideResult> {
    return (await apiClient.post<DecideResult>(`${BASE}/takeoff/tuning-sweeps/${sweepId}/decide`, body)).data;
  },
  async remove(sweepId: string): Promise<{ deleted: number }> {
    return (await apiClient.delete<{ deleted: number }>(`${BASE}/takeoff/tuning-sweeps/${sweepId}`)).data;
  },
};
