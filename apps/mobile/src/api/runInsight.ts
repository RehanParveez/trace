import { authenticatedRequest } from "./client";
import type { CalcUsage, ElementImpact, OrgCalcMetrics, RunMetrics } from "./types";

const BASE = "/drawings-boq";

export function getRunMetrics(runId: string): Promise<RunMetrics> {
  return authenticatedRequest<RunMetrics>(`${BASE}/calculation-runs/${runId}/metrics`);
}

export function getElementImpact(runId: string, elementId: string): Promise<ElementImpact> {
  return authenticatedRequest<ElementImpact>(
    `${BASE}/calculation-runs/${runId}/elements/${elementId}/impact`,
  );
}

export function getOrgMetrics(days: number): Promise<OrgCalcMetrics> {
  return authenticatedRequest<OrgCalcMetrics>(`${BASE}/calculation-metrics?days=${days}`);
}

export function getCalcUsage(): Promise<CalcUsage> {
  return authenticatedRequest<CalcUsage>(`${BASE}/calculation-usage`);
}