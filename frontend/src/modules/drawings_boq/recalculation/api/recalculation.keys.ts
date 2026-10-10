export const recalculationKeys = {
  all: ["scale"] as const,
  usage: () => [...recalculationKeys.all, "usage"] as const,
  runMetrics: (runId: string, status: string) => [...recalculationKeys.all, "run-metrics", runId, status] as const,
  orgMetrics: (days: number) => [...recalculationKeys.all, "org-metrics", days] as const,
  orgMetricsAll: () => [...recalculationKeys.all, "org-metrics"] as const,
  impact: (runId: string, elementId: string) => [...recalculationKeys.all, "impact", runId, elementId] as const,
  exportJob: (jobId: string) => [...recalculationKeys.all, "export-job", jobId] as const,
};