import { useMutation, useQuery } from "@tanstack/react-query";
import { recalculationApi } from "../api/recalculation.api";
import { recalculationKeys } from "../api/recalculation.keys";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import type { ExportJob } from "../types/recalculation.types";
import { isRunActive } from "../../utils/drawings-boq.utils";
import type { CalculationRunStatus } from "../../types/drawings-boq.types";
import { exportJobFilename, isExportJobActive } from "../utils/recalculation.utils";

export { recalculationKeys };

export function useRunMetrics(runId: string | undefined, runStatus: string | undefined) {
  return useQuery({
    queryKey: recalculationKeys.runMetrics(runId ?? "", runStatus ?? ""),
    queryFn: () => recalculationApi.getRunMetrics(runId as string),
    enabled: Boolean(runId),
    refetchInterval: isRunActive(runStatus as CalculationRunStatus | undefined) ? 5000 : false,
  });
}

export function useElementImpact(runId: string | undefined, elementId: string | undefined) {
  return useQuery({
    queryKey: recalculationKeys.impact(runId ?? "", elementId ?? ""),
    queryFn: () => recalculationApi.getElementImpact(runId as string, elementId as string),
    enabled: Boolean(runId && elementId),
    retry: false,
  });
}

export function useCalcUsage(enabled = true) {
  return useQuery({
    queryKey: recalculationKeys.usage(),
    queryFn: () => recalculationApi.getUsage(),
    enabled,
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useOrgCalcMetrics(days: number, enabled = true) {
  return useQuery({
    queryKey: recalculationKeys.orgMetrics(days),
    queryFn: () => recalculationApi.getOrgMetrics(days),
    enabled,
    staleTime: 30_000,
  });
}

export function useExportJob(initial: ExportJob) {
  return useQuery({
    queryKey: recalculationKeys.exportJob(initial.id),
    queryFn: () => recalculationApi.getExportJob(initial.id),
    initialData: initial,
    refetchInterval: (query) => (isExportJobActive(query.state.data?.status) ? 2000 : false),
  });
}

export function useDownloadExportJob() {
  return useMutation({
    mutationFn: async (job: ExportJob) => {
      const { blob, filename } = await recalculationApi.downloadExportJob(job.id, exportJobFilename(job));
      triggerBlobDownload(blob, filename);
      return filename;
    },
  });
}