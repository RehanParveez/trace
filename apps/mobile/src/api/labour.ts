import { authenticatedRequest } from "./client";
import type {LabourAdvance, LabourAdvanceCreatePayload, LabourAttendance, LabourAttendanceBulkResult, LabourAttendanceEntry, LabourBalance, LabourCost, LabourDayAttendanceSummary, LabourDeployment, LabourDeploymentCreatePayload,
  LabourDeploymentUpdatePayload, LabourPayment, LabourPaymentCreatePayload, LabourSource, LabourSourceCreatePayload, LabourSourceUpdatePayload, LabourSummary, LabourWorker, LabourWorkerCreatePayload, LabourWorkerUpdatePayload,
} from "./types";

const body = (value: unknown) => JSON.stringify(value);

export const listLabourSources = () =>
  authenticatedRequest<LabourSource[]>("/labour/sources");

export const createLabourSource = (payload: LabourSourceCreatePayload) =>
  authenticatedRequest<LabourSource>("/labour/sources", {
    method: "POST",
    body: body(payload),
  });

export const updateLabourSource = (
  sourceId: string,
  payload: LabourSourceUpdatePayload,
) =>
  authenticatedRequest<LabourSource>(`/labour/sources/${sourceId}`, {
    method: "PATCH",
    body: body(payload),
  });

export const listLabourWorkers = (sourceId?: string) => {
  const query = sourceId ? `?source_id=${encodeURIComponent(sourceId)}` : "";
  return authenticatedRequest<LabourWorker[]>(`/labour/workers${query}`);
};

export const createLabourWorker = (payload: LabourWorkerCreatePayload) =>
  authenticatedRequest<LabourWorker>("/labour/workers", {
    method: "POST",
    body: body(payload),
  });

export const updateLabourWorker = (
  workerId: string,
  payload: LabourWorkerUpdatePayload,
) =>
  authenticatedRequest<LabourWorker>(`/labour/workers/${workerId}`, {
    method: "PATCH",
    body: body(payload),
  });

export const listLabourDeployments = (projectId: string) =>
  authenticatedRequest<LabourDeployment[]>(
    `/labour/projects/${projectId}/deployments`,
  );

export const createLabourDeployment = (
  projectId: string,
  payload: LabourDeploymentCreatePayload,
) =>
  authenticatedRequest<LabourDeployment>(
    `/labour/projects/${projectId}/deployments`,
    { method: "POST", body: body(payload) },
  );

export const updateLabourDeployment = (
  projectId: string,
  deploymentId: string,
  payload: LabourDeploymentUpdatePayload,
) =>
  authenticatedRequest<LabourDeployment>(
    `/labour/projects/${projectId}/deployments/${deploymentId}`,
    { method: "PATCH", body: body(payload) },
  );

export const listLabourAttendance = (
  projectId: string,
  periodStart?: string,
  periodEnd?: string,
) => {
  const query = new URLSearchParams();
  if (periodStart) query.set("period_start", periodStart);
  if (periodEnd) query.set("period_end", periodEnd);
  const suffix = query.size ? `?${query.toString()}` : "";

  return authenticatedRequest<LabourAttendance[]>(
    `/labour/projects/${projectId}/attendance${suffix}`,
  );
};

export const bulkRecordLabourAttendance = (
  projectId: string,
  entries: LabourAttendanceEntry[],
) =>
  authenticatedRequest<LabourAttendanceBulkResult>(
    `/labour/projects/${projectId}/attendance/bulk`,
    { method: "POST", body: body({ entries }) },
  );

export const getLabourDaySummary = (projectId: string, date: string) =>
  authenticatedRequest<LabourDayAttendanceSummary>(
    `/labour/projects/${projectId}/attendance/day-summary?attendance_date=${encodeURIComponent(date)}`,
  );

export const getLabourCost = (
  projectId: string,
  periodStart: string,
  periodEnd: string,
  sourceId?: string,
  workerId?: string,
) => {
  const query = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
  });
  if (sourceId) query.set("source_id", sourceId);
  if (workerId) query.set("worker_id", workerId);

  return authenticatedRequest<LabourCost>(
    `/labour/projects/${projectId}/cost?${query.toString()}`,
  );
};

export const getLabourBalance = (
  projectId: string,
  sourceId: string,
  workerId?: string,
) => {
  const query = new URLSearchParams({ source_id: sourceId });
  if (workerId) query.set("worker_id", workerId);

  return authenticatedRequest<LabourBalance>(
    `/labour/projects/${projectId}/balance?${query.toString()}`,
  );
};

export const listLabourAdvances = (projectId: string) =>
  authenticatedRequest<LabourAdvance[]>(
    `/labour/projects/${projectId}/advances`,
  );

export const createLabourAdvance = (
  projectId: string,
  payload: LabourAdvanceCreatePayload,
) =>
  authenticatedRequest<LabourAdvance>(
    `/labour/projects/${projectId}/advances`,
    { method: "POST", body: body(payload) },
  );

export const listLabourPayments = (projectId: string) =>
  authenticatedRequest<LabourPayment[]>(
    `/labour/projects/${projectId}/payments`,
  );

export const createLabourPayment = (
  projectId: string,
  payload: LabourPaymentCreatePayload,
) =>
  authenticatedRequest<LabourPayment>(
    `/labour/projects/${projectId}/payments`,
    { method: "POST", body: body(payload) },
  );

export const getLabourSummary = (
  projectId: string,
  periodStart: string,
  periodEnd: string,
) => {
  const query = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
  });

  return authenticatedRequest<LabourSummary>(
    `/labour/projects/${projectId}/summary?${query.toString()}`,
  );
};