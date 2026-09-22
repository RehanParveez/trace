import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { withholdingTaxApi } from "../api/withholding-tax.api";
import type { WHTCategory } from "../types/withholding-tax.types";

export const whtKeys = {
  all: ["withholding-tax"] as const,
  rates: () => [...whtKeys.all, "rates"] as const,
  deductions: (start?: string, end?: string, projectId?: string) => [...whtKeys.all, "deductions", start, end, projectId] as const,
  summary: (start: string, end: string) => [...whtKeys.all, "summary", start, end] as const,
};

export function useWHTRates() {
  return useQuery({ queryKey: whtKeys.rates(), queryFn: withholdingTaxApi.listRates });
}
export function useCreateWHTRate() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: Parameters<typeof withholdingTaxApi.createRate>[0]) => withholdingTaxApi.createRate(payload), onSuccess: () => void qc.invalidateQueries({ queryKey: whtKeys.rates() }) });
}
export function useUpdateWHTRate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ rateId, payload }: { rateId: string; payload: Parameters<typeof withholdingTaxApi.updateRate>[1] }) => withholdingTaxApi.updateRate(rateId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: whtKeys.rates() }),
  });
}

export function useWHTPreview(category: WHTCategory | null, grossAmount: number, isFiler: boolean, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...whtKeys.all, "preview", category, grossAmount, isFiler],
    queryFn: () => withholdingTaxApi.preview(category as WHTCategory, grossAmount, isFiler),
    enabled: Boolean(category) && grossAmount > 0 && (options?.enabled ?? true),
    retry: false,
  });
}

export function useWHTDeductions(periodStart?: string, periodEnd?: string, projectId?: string) {
  return useQuery({ queryKey: whtKeys.deductions(periodStart, periodEnd, projectId), queryFn: () => withholdingTaxApi.listDeductions(periodStart, periodEnd, projectId) });
}
export function useWHTRegisterSummary(periodStart: string, periodEnd: string) {
  return useQuery({ queryKey: whtKeys.summary(periodStart, periodEnd), queryFn: () => withholdingTaxApi.getRegisterSummary(periodStart, periodEnd), enabled: Boolean(periodStart && periodEnd) });
}