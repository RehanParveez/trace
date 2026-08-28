import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { subscriptionsApi } from "../api/subscriptions.api";
import type {CancelSubscriptionRequest, ChangePlanRequest,
} from "../types/subscription.types";

export const subscriptionKeys = {
  all: ["subscriptions"] as const,

  plans: () =>
    [...subscriptionKeys.all, "plans"] as const,

  current: () =>
    [...subscriptionKeys.all, "current"] as const,

  usage: () =>
    [...subscriptionKeys.all, "usage"] as const,
};

export function useSubscriptionPlans() {
  return useQuery({
    queryKey: subscriptionKeys.plans(),
    queryFn: subscriptionsApi.listPlans,
  });
}

export function useSubscription() {
  return useQuery({
    queryKey: subscriptionKeys.current(),
    queryFn: subscriptionsApi.getSubscription,
  });
}

export function useSubscriptionUsage() {
  return useQuery({
    queryKey: subscriptionKeys.usage(),
    queryFn: subscriptionsApi.getUsage,
  });
}

export function useChangePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ChangePlanRequest) =>
      subscriptionsApi.changePlan(payload),

    onSuccess: (subscription) => {
      queryClient.setQueryData(
        subscriptionKeys.current(),
        subscription,
      );

      void queryClient.invalidateQueries({
        queryKey: subscriptionKeys.usage(),
      });
    },
  });
}

export function useCancelSubscription() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CancelSubscriptionRequest) =>
      subscriptionsApi.cancelSubscription(payload),

    onSuccess: (subscription) => {
      queryClient.setQueryData(
        subscriptionKeys.current(),
        subscription,
      );

      void queryClient.invalidateQueries({
        queryKey: subscriptionKeys.usage(),
      });
    },
  });
}