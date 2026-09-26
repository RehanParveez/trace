import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { salesTaxApi } from "../api/sales-tax.api";
import type { SalesTaxAuthority } from "../types/sales-tax.types";

export const salesTaxKeys = {
  all: ["sales-tax"] as const,
  rates: () => [...salesTaxKeys.all, "rates"] as const,
  charges: (start?: string, end?: string, projectId?: string) => [...salesTaxKeys.all, "charges", start, end, projectId] as const,
  summary: (start: string, end: string) => [...salesTaxKeys.all, "summary", start, end] as const,
};

export function useSalesTaxRates() {
  return useQuery({ queryKey: salesTaxKeys.rates(), queryFn: salesTaxApi.listRates });
}
export function useCreateSalesTaxRate() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: Parameters<typeof salesTaxApi.createRate>[0]) => salesTaxApi.createRate(payload), onSuccess: () => void qc.invalidateQueries({ queryKey: salesTaxKeys.rates() }) });
}
export function useUpdateSalesTaxRate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ rateId, payload }: { rateId: string; payload: Parameters<typeof salesTaxApi.updateRate>[1] }) => salesTaxApi.updateRate(rateId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: salesTaxKeys.rates() }),
  });
}

export function useSalesTaxPreview(authority: SalesTaxAuthority | null, taxableAmount: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...salesTaxKeys.all, "preview", authority, taxableAmount],
    queryFn: () => salesTaxApi.preview(authority as SalesTaxAuthority, taxableAmount),
    enabled: Boolean(authority) && taxableAmount > 0 && (options?.enabled ?? true),
    retry: false,
  });
}

export function useSalesTaxCharges(periodStart?: string, periodEnd?: string, projectId?: string) {
  return useQuery({ queryKey: salesTaxKeys.charges(periodStart, periodEnd, projectId), queryFn: () => salesTaxApi.listCharges(periodStart, periodEnd, projectId) });
}
export function useSalesTaxRegisterSummary(periodStart: string, periodEnd: string) {
  return useQuery({ queryKey: salesTaxKeys.summary(periodStart, periodEnd), queryFn: () => salesTaxApi.getRegisterSummary(periodStart, periodEnd), enabled: Boolean(periodStart && periodEnd) });
}