import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { labourApi } from "../api/labour.api";

export const labourKeys = {
  all: ["labour"] as const,
  sources: () => [...labourKeys.all, "sources"] as const,
  workers: (sourceId?: string) => [...labourKeys.all, "workers", sourceId] as const,
  deployments: (projectId: string) => [...labourKeys.all, "deployments", projectId] as const,
  advances: (projectId: string) => [...labourKeys.all, "advances", projectId] as const,
  payments: (projectId: string) => [...labourKeys.all, "payments", projectId] as const,
  summary: (projectId: string, start: string, end: string) => [...labourKeys.all, "summary", projectId, start, end] as const,
  daySummary: (projectId: string, date: string) => [...labourKeys.all, "day-summary", projectId, date] as const,
};

export function useLabourSources() {
  return useQuery({ queryKey: labourKeys.sources(), queryFn: labourApi.listSources });
}
export function useCreateLabourSource() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: labourApi.createSource, onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.sources() }) });
}
export function useLabourWorkers(sourceId?: string) {
  return useQuery({ queryKey: labourKeys.workers(sourceId), queryFn: () => labourApi.listWorkers(sourceId) });
}
export function useCreateLabourWorker() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: Parameters<typeof labourApi.createWorker>[0]) => labourApi.createWorker(payload), onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.all }) });
}
export function useLabourDeployments(projectId: string) {
  return useQuery({ queryKey: labourKeys.deployments(projectId), queryFn: () => labourApi.listDeployments(projectId), enabled: Boolean(projectId) });
}
export function useCreateLabourDeployment(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof labourApi.createDeployment>[1]) => labourApi.createDeployment(projectId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.deployments(projectId) }),
  });
}
export function useEndLabourDeployment(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ deploymentId, endDate }: { deploymentId: string; endDate: string }) => labourApi.endDeployment(projectId, deploymentId, endDate),
    onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.deployments(projectId) }),
  });
}
export function useBulkRecordAttendance(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entries: Parameters<typeof labourApi.bulkRecordAttendance>[1]) => labourApi.bulkRecordAttendance(projectId, entries),
    onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.all }),
  });
}
export function useLabourDaySummary(projectId: string, date: string) {
  return useQuery({ queryKey: labourKeys.daySummary(projectId, date), queryFn: () => labourApi.getDaySummary(projectId, date), enabled: Boolean(projectId && date) });
}
export function useLabourAdvances(projectId: string) {
  return useQuery({ queryKey: labourKeys.advances(projectId), queryFn: () => labourApi.listAdvances(projectId), enabled: Boolean(projectId) });
}
export function useCreateLabourAdvance(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof labourApi.createAdvance>[1]) => labourApi.createAdvance(projectId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.all }),
  });
}
export function useLabourPayments(projectId: string) {
  return useQuery({ queryKey: labourKeys.payments(projectId), queryFn: () => labourApi.listPayments(projectId), enabled: Boolean(projectId) });
}
export function useCreateLabourPayment(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof labourApi.createPayment>[1]) => labourApi.createPayment(projectId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: labourKeys.all }),
  });
}
export function useLabourSummary(projectId: string, periodStart: string, periodEnd: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: labourKeys.summary(projectId, periodStart, periodEnd),
    queryFn: () => labourApi.getSummary(projectId, periodStart, periodEnd),
    enabled: Boolean(projectId && periodStart && periodEnd) && (options?.enabled ?? true),
  });
}