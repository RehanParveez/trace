import { apiClient } from "../../../shared/api/client";
import type {DayAttendanceSummary, LabourAdvance, LabourAttendance, LabourBalance, LabourCost, LabourDeployment, LabourPayment, LabourSource, LabourSummary, LabourWorker,
} from "../types/labour.types";

export const labourApi = {
  async listSources(): Promise<LabourSource[]> {
    return (await apiClient.get<LabourSource[]>("/labour/sources")).data;
  },
  async createSource(payload: { name: string; source_type: string; contact_name?: string | null; contact_phone?: string | null; notes?: string | null }): Promise<LabourSource> {
    return (await apiClient.post<LabourSource>("/labour/sources", payload)).data;
  },
  async listWorkers(sourceId?: string): Promise<LabourWorker[]> {
    return (await apiClient.get<LabourWorker[]>("/labour/workers", { params: { source_id: sourceId } })).data;
  },
  async createWorker(payload: { source_id: string; name: string; trade: string; cnic?: string | null; phone?: string | null; default_daily_rate?: number | null }): Promise<LabourWorker> {
    return (await apiClient.post<LabourWorker>("/labour/workers", payload)).data;
  },
  async listDeployments(projectId: string): Promise<LabourDeployment[]> {
    return (await apiClient.get<LabourDeployment[]>(`/labour/projects/${projectId}/deployments`)).data;
  },
  async createDeployment(projectId: string, payload: { source_id: string; worker_id?: string | null; trade: string; daily_rate: number; start_date: string }): Promise<LabourDeployment> {
    return (await apiClient.post<LabourDeployment>(`/labour/projects/${projectId}/deployments`, payload)).data;
  },
  async endDeployment(projectId: string, deploymentId: string, endDate: string): Promise<LabourDeployment> {
    return (await apiClient.patch<LabourDeployment>(`/labour/projects/${projectId}/deployments/${deploymentId}`, { status: "ENDED", end_date: endDate })).data;
  },
  async bulkRecordAttendance(projectId: string, entries: { deployment_id: string; attendance_date: string; units_present: number; notes?: string | null }[]): Promise<{ created: number; updated: number; items: LabourAttendance[] }> {
    return (await apiClient.post(`/labour/projects/${projectId}/attendance/bulk`, { entries })).data;
  },
  async getDaySummary(projectId: string, date: string): Promise<DayAttendanceSummary> {
    return (await apiClient.get<DayAttendanceSummary>(`/labour/projects/${projectId}/attendance/day-summary`, { params: { attendance_date: date } })).data;
  },
  async getCost(projectId: string, periodStart: string, periodEnd: string, sourceId?: string, workerId?: string): Promise<LabourCost> {
    return (await apiClient.get<LabourCost>(`/labour/projects/${projectId}/cost`, { params: { period_start: periodStart, period_end: periodEnd, source_id: sourceId, worker_id: workerId } })).data;
  },
  async getBalance(projectId: string, sourceId: string, workerId?: string): Promise<LabourBalance> {
    return (await apiClient.get<LabourBalance>(`/labour/projects/${projectId}/balance`, { params: { source_id: sourceId, worker_id: workerId } })).data;
  },
  async listAdvances(projectId: string): Promise<LabourAdvance[]> {
    return (await apiClient.get<LabourAdvance[]>(`/labour/projects/${projectId}/advances`)).data;
  },
  async createAdvance(projectId: string, payload: { source_id: string; worker_id?: string | null; amount: number; advance_date: string; notes?: string | null }): Promise<LabourAdvance> {
    return (await apiClient.post<LabourAdvance>(`/labour/projects/${projectId}/advances`, payload)).data;
  },
  async listPayments(projectId: string): Promise<LabourPayment[]> {
    return (await apiClient.get<LabourPayment[]>(`/labour/projects/${projectId}/payments`)).data;
  },
  async createPayment(projectId: string, payload: { source_id: string; worker_id?: string | null; period_start: string; period_end: string; gross_wage_amount: number; advance_recovered_amount?: number; payment_date: string; notes?: string | null }): Promise<LabourPayment> {
    return (await apiClient.post<LabourPayment>(`/labour/projects/${projectId}/payments`, payload)).data;
  },
  async getSummary(projectId: string, periodStart: string, periodEnd: string): Promise<LabourSummary> {
    return (await apiClient.get<LabourSummary>(`/labour/projects/${projectId}/summary`, { params: { period_start: periodStart, period_end: periodEnd } })).data;
  },
};