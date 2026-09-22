import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { subcontractorsApi } from "../api/subcontractors.api";

export const subcontractorKeys = {
  all: ["subcontractors"] as const,
  list: () => [...subcontractorKeys.all, "list"] as const,
  agreements: (projectId: string) => [...subcontractorKeys.all, "agreements", projectId] as const,
  agreement: (agreementId: string) => [...subcontractorKeys.all, "agreement", agreementId] as const,
  bills: (agreementId: string) => [...subcontractorKeys.all, "bills", agreementId] as const,
  bill: (billId: string) => [...subcontractorKeys.all, "bill", billId] as const,
  advances: (agreementId: string) => [...subcontractorKeys.all, "advances", agreementId] as const,
  payments: (agreementId: string) => [...subcontractorKeys.all, "payments", agreementId] as const,
  ledger: (agreementId: string) => [...subcontractorKeys.all, "ledger", agreementId] as const,
  projectCost: (projectId: string) => [...subcontractorKeys.all, "project-cost", projectId] as const,
};

export function useSubcontractors() {
  return useQuery({ queryKey: subcontractorKeys.list(), queryFn: subcontractorsApi.list });
}
export function useCreateSubcontractor() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: subcontractorsApi.create, onSuccess: () => void qc.invalidateQueries({ queryKey: subcontractorKeys.list() }) });
}

export function useAgreements(projectId: string) {
  return useQuery({ queryKey: subcontractorKeys.agreements(projectId), queryFn: () => subcontractorsApi.listAgreements(projectId), enabled: Boolean(projectId) });
}
export function useAgreement(agreementId: string | undefined) {
  return useQuery({ queryKey: subcontractorKeys.agreement(agreementId ?? ""), queryFn: () => subcontractorsApi.getAgreement(agreementId as string), enabled: Boolean(agreementId) });
}
export function useCreateAgreement(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<Parameters<typeof subcontractorsApi.createAgreement>[0], "project_id">) => subcontractorsApi.createAgreement({ ...payload, project_id: projectId }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: subcontractorKeys.agreements(projectId) }),
  });
}

export function useProjectSubcontractCost(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({ queryKey: subcontractorKeys.projectCost(projectId), queryFn: () => subcontractorsApi.getProjectCostSummary(projectId), enabled: Boolean(projectId) && (options?.enabled ?? true) });
}

export function useBills(agreementId: string) {
  return useQuery({ queryKey: subcontractorKeys.bills(agreementId), queryFn: () => subcontractorsApi.listBills(agreementId), enabled: Boolean(agreementId) });
}
export function useBill(billId: string | undefined) {
  return useQuery({ queryKey: subcontractorKeys.bill(billId ?? ""), queryFn: () => subcontractorsApi.getBill(billId as string), enabled: Boolean(billId) });
}
export function useCreateBill(agreementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof subcontractorsApi.createBill>[1]) => subcontractorsApi.createBill(agreementId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: subcontractorKeys.bills(agreementId) }),
  });
}
export function useIssueBill(agreementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, version }: { billId: string; version: number }) => subcontractorsApi.issueBill(billId, version),
    onSuccess: (bill) => { void qc.invalidateQueries({ queryKey: subcontractorKeys.bills(agreementId) }); void qc.invalidateQueries({ queryKey: subcontractorKeys.bill(bill.id) }); void qc.invalidateQueries({ queryKey: subcontractorKeys.ledger(agreementId) }); },
  });
}
export function useCancelBill(agreementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, version }: { billId: string; version: number }) => subcontractorsApi.cancelBill(billId, version),
    onSuccess: (bill) => { void qc.invalidateQueries({ queryKey: subcontractorKeys.bills(agreementId) }); void qc.invalidateQueries({ queryKey: subcontractorKeys.bill(bill.id) }); },
  });
}

export function useAdvances(agreementId: string) {
  return useQuery({ queryKey: subcontractorKeys.advances(agreementId), queryFn: () => subcontractorsApi.listAdvances(agreementId), enabled: Boolean(agreementId) });
}
export function useCreateAdvance(agreementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof subcontractorsApi.recordAdvance>[1]) => subcontractorsApi.recordAdvance(agreementId, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: subcontractorKeys.advances(agreementId) }); void qc.invalidateQueries({ queryKey: subcontractorKeys.ledger(agreementId) }); },
  });
}

export function usePayments(agreementId: string) {
  return useQuery({ queryKey: subcontractorKeys.payments(agreementId), queryFn: () => subcontractorsApi.listPayments(agreementId), enabled: Boolean(agreementId) });
}
export function useCreatePayment(agreementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof subcontractorsApi.recordPayment>[1]) => subcontractorsApi.recordPayment(agreementId, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: subcontractorKeys.payments(agreementId) }); void qc.invalidateQueries({ queryKey: subcontractorKeys.ledger(agreementId) }); },
  });
}

export function useLedger(agreementId: string, options?: { enabled?: boolean }) {
  return useQuery({ queryKey: subcontractorKeys.ledger(agreementId), queryFn: () => subcontractorsApi.getLedger(agreementId), enabled: Boolean(agreementId) && (options?.enabled ?? true) });
}