import { useSubscriptionUsage } from "./useSubscription";

export interface QuotaStatus {
  isLoading: boolean;
  hasQuota: boolean;
  limit: number | null;
  used: number;
  remaining: number | null;
  isAtLimit: boolean;
  isNearLimit: boolean;
}

export function useQuotaStatus(metric: string): QuotaStatus {
  const usageQuery = useSubscriptionUsage();

  const found = usageQuery.data?.metrics.find((item) => item.metric === metric);

  if (!found) {
    return {
      isLoading: usageQuery.isLoading,
      hasQuota: false,
      limit: null,
      used: 0,
      remaining: null,
      isAtLimit: false,
      isNearLimit: false,
    };
  }

  const isAtLimit = found.limit !== null && found.used >= found.limit;
  const isNearLimit =
    found.limit !== null && found.limit > 0 && found.used / found.limit >= 0.8;

  return {
    isLoading: usageQuery.isLoading,
    hasQuota: true,
    limit: found.limit,
    used: found.used,
    remaining: found.remaining,
    isAtLimit,
    isNearLimit,
  };
}