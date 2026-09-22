import { apiClient } from "../../../shared/api/client";
import type {AgreementItem, ProjectSubcontractCost, Subcontractor, SubcontractAgreement,  SubcontractAgreementDetail, SubcontractorAdvance, SubcontractorBill, SubcontractorBillDetail,
  SubcontractorLedger, SubcontractorPayment,
} from "../types/subcontractor.types";

export const subcontractorsApi = {
  async list(): Promise<Subcontractor[]> { return (await apiClient.get<Subcontractor[]>("/subcontractors")).data; },
  async create(payload: { name: string; trade_specialization: string; contact_name?: string | null; contact_phone?: string | null; ntn_or_cnic?: string | null; notes?: string | null }): Promise<Subcontractor> {
    return (await apiClient.post<Subcontractor>("/subcontractors", payload)).data;
  },

  async listAgreements(projectId: string): Promise<SubcontractAgreementDetail[]> {
    return (await apiClient.get<SubcontractAgreementDetail[]>(`/subcontractors/projects/${projectId}/agreements`)).data;
  },
  async getAgreement(agreementId: string): Promise<SubcontractAgreementDetail> {
    return (await apiClient.get<SubcontractAgreementDetail>(`/subcontractors/agreements/${agreementId}`)).data;
  },
  async createAgreement(payload: {
    project_id: string; subcontractor_id: string; scope_description: string; start_date: string;
    default_retention_percentage?: number; default_retention_cap_percentage?: number | null; notes?: string | null;
    items?: { description: string; unit: string; quantity: number; rate: number }[]; contract_value?: number;
  }): Promise<SubcontractAgreementDetail> {
    return (await apiClient.post<SubcontractAgreementDetail>("/subcontractors/agreements", payload)).data;
  },

  async getProjectCostSummary(projectId: string): Promise<ProjectSubcontractCost> {
    return (await apiClient.get<ProjectSubcontractCost>(`/subcontractors/projects/${projectId}/cost-summary`)).data;
  },

  async createBill(agreementId: string, payload: {
    period_start: string; period_end: string; retention_percentage?: number | null;
    retention_cap_percentage?: number | null; other_deductions_amount?: number; other_deductions_note?: string | null;
    notes?: string | null; measurements: { agreement_item_id: string; cumulative_percentage: number }[];
  }): Promise<SubcontractorBillDetail> {
    return (await apiClient.post<SubcontractorBillDetail>(`/subcontractors/agreements/${agreementId}/bills`, payload)).data;
  },
  async listBills(agreementId: string): Promise<SubcontractorBill[]> {
    return (await apiClient.get<SubcontractorBill[]>(`/subcontractors/agreements/${agreementId}/bills`)).data;
  },
  async getBill(billId: string): Promise<SubcontractorBillDetail> {
    return (await apiClient.get<SubcontractorBillDetail>(`/subcontractors/bills/${billId}`)).data;
  },
  async issueBill(billId: string, version: number): Promise<SubcontractorBill> {
    return (await apiClient.post<SubcontractorBill>(`/subcontractors/bills/${billId}/issue`, { version })).data;
  },
  async cancelBill(billId: string, version: number): Promise<SubcontractorBill> {
    return (await apiClient.post<SubcontractorBill>(`/subcontractors/bills/${billId}/cancel`, { version })).data;
  },
  async downloadBillPdf(billId: string): Promise<Blob> { return (await apiClient.get(`/subcontractors/bills/${billId}/export/pdf`, { responseType: "blob" })).data; },
  async downloadBillXlsx(billId: string): Promise<Blob> { return (await apiClient.get(`/subcontractors/bills/${billId}/export/xlsx`, { responseType: "blob" })).data; },

  async recordAdvance(agreementId: string, payload: { amount: number; advance_date: string; notes?: string | null }): Promise<SubcontractorAdvance> {
    return (await apiClient.post<SubcontractorAdvance>(`/subcontractors/agreements/${agreementId}/advances`, payload)).data;
  },
  async listAdvances(agreementId: string): Promise<SubcontractorAdvance[]> {
    return (await apiClient.get<SubcontractorAdvance[]>(`/subcontractors/agreements/${agreementId}/advances`)).data;
  },
  async recordPayment(agreementId: string, payload: { bill_id?: string | null; gross_amount: number; advance_recovered_amount?: number; payment_date: string; notes?: string | null }): Promise<SubcontractorPayment> {
    return (await apiClient.post<SubcontractorPayment>(`/subcontractors/agreements/${agreementId}/payments`, payload)).data;
  },
  async listPayments(agreementId: string): Promise<SubcontractorPayment[]> {
    return (await apiClient.get<SubcontractorPayment[]>(`/subcontractors/agreements/${agreementId}/payments`)).data;
  },
  async getLedger(agreementId: string): Promise<SubcontractorLedger> {
    return (await apiClient.get<SubcontractorLedger>(`/subcontractors/agreements/${agreementId}/ledger`)).data;
  },
};