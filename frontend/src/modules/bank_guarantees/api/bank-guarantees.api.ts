import { apiClient } from "../../../shared/api/client";
import type { BankGuarantee, BankGuaranteeHolderType, ProjectBankGuaranteeSummary } from "../types/bank-guarantee.types";

export const bankGuaranteesApi = {
  async list(projectId: string): Promise<BankGuarantee[]> {
    return (await apiClient.get<BankGuarantee[]>("/bank-guarantees", { params: { project_id: projectId } })).data;
  },
  async get(id: string): Promise<BankGuarantee> {
    return (await apiClient.get<BankGuarantee>(`/bank-guarantees/${id}`)).data;
  },
  async create(payload: {
    holder_type: BankGuaranteeHolderType; project_id: string; boq_version_id?: string | null; agreement_id?: string | null;
    guarantee_number: string; issuing_bank: string; amount: number; issue_date: string; expiry_date: string; notes?: string | null;
  }): Promise<BankGuarantee> {
    return (await apiClient.post<BankGuarantee>("/bank-guarantees", payload)).data;
  },
  async renew(id: string, payload: { guarantee_number: string; issue_date: string; expiry_date: string; amount?: number | null; notes?: string | null }): Promise<BankGuarantee> {
    return (await apiClient.post<BankGuarantee>(`/bank-guarantees/${id}/renew`, payload)).data;
  },
  async release(id: string): Promise<BankGuarantee> {
    return (await apiClient.post<BankGuarantee>(`/bank-guarantees/${id}/release`, {})).data;
  },
  async markCalled(id: string): Promise<BankGuarantee> {
    return (await apiClient.post<BankGuarantee>(`/bank-guarantees/${id}/mark-called`, {})).data;
  },
  async getProjectSummary(projectId: string): Promise<ProjectBankGuaranteeSummary> {
    return (await apiClient.get<ProjectBankGuaranteeSummary>(`/bank-guarantees/projects/${projectId}/summary`)).data;
  },
};