import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { billingProfileApi } from "../api/billingProfile.api";
import type { BillingProfileSetting } from "../api/billingProfile.api";

const KEY = ["organizations", "billing-profile"] as const;

export function useBillingProfile() {
  return useQuery<BillingProfileSetting>({ queryKey: KEY, queryFn: billingProfileApi.get });
}

export function useSetBillingProfile() {
  const qc = useQueryClient();
  return useMutation<BillingProfileSetting, unknown, string | null>({
    mutationFn: (value) => billingProfileApi.set(value),
    onSuccess: (data) => {
      qc.setQueryData(KEY, data);
    },
  });
}
