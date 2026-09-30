import { authenticatedRequest, authenticatedResponse, } from "./client";
import type {ProjectSubcontractCost, SubcontractAgreementCreatePayload, SubcontractAgreementDetail, SubcontractAgreementUpdatePayload, Subcontractor, SubcontractorAdvance, SubcontractorAdvanceCreatePayload,
  SubcontractorBill, SubcontractorBillCreatePayload, SubcontractorBillDetail, SubcontractorCreatePayload, SubcontractorLedger, SubcontractorPayment, SubcontractorPaymentCreatePayload, SubcontractorUpdatePayload, SubcontractAgreement
} from "./types";

const body = (value: unknown) => JSON.stringify(value);

export const listSubcontractors = () =>
  authenticatedRequest<Subcontractor[]>("/subcontractors");

export const createSubcontractor = (payload: SubcontractorCreatePayload) =>
  authenticatedRequest<Subcontractor>("/subcontractors", {
    method: "POST",
    body: body(payload),
  });

export const updateSubcontractor = (
  subcontractorId: string,
  payload: SubcontractorUpdatePayload,
) =>
  authenticatedRequest<Subcontractor>(
    `/subcontractors/${subcontractorId}`,
    { method: "PATCH", body: body(payload) },
  );

export const listProjectAgreements = (projectId: string) =>
  authenticatedRequest<SubcontractAgreementDetail[]>(
    `/subcontractors/projects/${projectId}/agreements`,
  );

export const getProjectSubcontractCost = (projectId: string) =>
  authenticatedRequest<ProjectSubcontractCost>(
    `/subcontractors/projects/${projectId}/cost-summary`,
  );

export const createAgreement = (
  payload: SubcontractAgreementCreatePayload,
) =>
  authenticatedRequest<SubcontractAgreementDetail>(
    "/subcontractors/agreements",
    { method: "POST", body: body(payload) },
  );

export const getAgreement = (agreementId: string) =>
  authenticatedRequest<SubcontractAgreementDetail>(
    `/subcontractors/agreements/${agreementId}`,
  );

export const updateAgreement = (
  agreementId: string,
  payload: SubcontractAgreementUpdatePayload,
) =>
  authenticatedRequest<SubcontractAgreement>(
    `/subcontractors/agreements/${agreementId}`,
    { method: "PATCH", body: body(payload) },
  );

export const listAgreementBills = (agreementId: string) =>
  authenticatedRequest<SubcontractorBill[]>(
    `/subcontractors/agreements/${agreementId}/bills`,
  );

export const createAgreementBill = (
  agreementId: string,
  payload: SubcontractorBillCreatePayload,
) =>
  authenticatedRequest<SubcontractorBillDetail>(
    `/subcontractors/agreements/${agreementId}/bills`,
    { method: "POST", body: body(payload) },
  );

export const getSubcontractorBill = (billId: string) =>
  authenticatedRequest<SubcontractorBillDetail>(
    `/subcontractors/bills/${billId}`,
  );

export const issueSubcontractorBill = (billId: string, version: number) =>
  authenticatedRequest<SubcontractorBill>(
    `/subcontractors/bills/${billId}/issue`,
    { method: "POST", body: body({ version }) },
  );

export const cancelSubcontractorBill = (billId: string, version: number) =>
  authenticatedRequest<SubcontractorBill>(
    `/subcontractors/bills/${billId}/cancel`,
    { method: "POST", body: body({ version }) },
  );

export const listAgreementAdvances = (agreementId: string) =>
  authenticatedRequest<SubcontractorAdvance[]>(
    `/subcontractors/agreements/${agreementId}/advances`,
  );

export const createAgreementAdvance = (
  agreementId: string,
  payload: SubcontractorAdvanceCreatePayload,
) =>
  authenticatedRequest<SubcontractorAdvance>(
    `/subcontractors/agreements/${agreementId}/advances`,
    { method: "POST", body: body(payload) },
  );

export const listAgreementPayments = (agreementId: string) =>
  authenticatedRequest<SubcontractorPayment[]>(
    `/subcontractors/agreements/${agreementId}/payments`,
  );

export const createAgreementPayment = (
  agreementId: string,
  payload: SubcontractorPaymentCreatePayload,
) =>
  authenticatedRequest<SubcontractorPayment>(
    `/subcontractors/agreements/${agreementId}/payments`,
    { method: "POST", body: body(payload) },
  );

export const getAgreementLedger = (agreementId: string) =>
  authenticatedRequest<SubcontractorLedger>(
    `/subcontractors/agreements/${agreementId}/ledger`,
  );

export async function downloadSubcontractorBillPdf(
  billId: string,
): Promise<ArrayBuffer> {
  const response = await authenticatedResponse(
    `/subcontractors/bills/${billId}/export/pdf`,
  );
  return response.arrayBuffer();
}

export async function downloadSubcontractorBillXlsx(
  billId: string,
): Promise<ArrayBuffer> {
  const response = await authenticatedResponse(
    `/subcontractors/bills/${billId}/export/xlsx`,
  );
  return response.arrayBuffer();
}