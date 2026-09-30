import { authenticatedRequest } from "./client";
import type {BankGuarantee, BankGuaranteeCreatePayload, BankGuaranteeRenewPayload, ProjectBankGuaranteeSummary,
} from "./types";

const body = (value: unknown) => JSON.stringify(value);

export const listProjectBankGuarantees = (projectId: string) =>
  authenticatedRequest<BankGuarantee[]>(
    `/bank-guarantees?project_id=${encodeURIComponent(projectId)}`,
  );

export const getBankGuarantee = (guaranteeId: string) =>
  authenticatedRequest<BankGuarantee>(
    `/bank-guarantees/${guaranteeId}`,
  );

export const getProjectBankGuaranteeSummary = (projectId: string) =>
  authenticatedRequest<ProjectBankGuaranteeSummary>(
    `/bank-guarantees/projects/${encodeURIComponent(projectId)}/summary`,
  );

export const createBankGuarantee = (payload: BankGuaranteeCreatePayload) =>
  authenticatedRequest<BankGuarantee>("/bank-guarantees", {
    method: "POST",
    body: body(payload),
  });

export const renewBankGuarantee = (
  guaranteeId: string,
  payload: BankGuaranteeRenewPayload,
) =>
  authenticatedRequest<BankGuarantee>(
    `/bank-guarantees/${guaranteeId}/renew`,
    { method: "POST", body: body(payload) },
  );

export const releaseBankGuarantee = (guaranteeId: string) =>
  authenticatedRequest<BankGuarantee>(
    `/bank-guarantees/${guaranteeId}/release`,
    { method: "POST" },
  );

export const markBankGuaranteeCalled = (guaranteeId: string) =>
  authenticatedRequest<BankGuarantee>(
    `/bank-guarantees/${guaranteeId}/mark-called`,
    { method: "POST" },
  );