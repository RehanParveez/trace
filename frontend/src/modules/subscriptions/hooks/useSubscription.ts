import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { subscriptionsApi } from "../api/subscriptions.api";
import type {
  AdminSubscriptionListParams, CancelSubscriptionRequest, ChangePlanRequest,
} from "../types/subscription.types";

export const subscriptionKeys = {
  all: ["subscriptions"] as const,

  plans: () =>
    [...subscriptionKeys.all, "plans"] as const,

  current: () =>
    [...subscriptionKeys.all, "current"] as const,

  summary: () =>
    [...subscriptionKeys.all, "summary"] as const,

  usage: () =>
    [...subscriptionKeys.all, "usage"] as const,

  admin: (params: AdminSubscriptionListParams) =>
    [...subscriptionKeys.all, "admin", params] as const,
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

export function useSubscriptionSummary() {
  return useQuery({
    queryKey: subscriptionKeys.summary(),
    queryFn: subscriptionsApi.getSubscriptionSummary,
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
    mutationFn: (variables: {
      payload: ChangePlanRequest;
      idempotencyKey?: string;
    }) =>
      subscriptionsApi.changePlan(
        variables.payload,
        variables.idempotencyKey,
      ),

    onSuccess: (subscription) => {
      queryClient.setQueryData(
        subscriptionKeys.current(),
        subscription,
      );

      void queryClient.invalidateQueries({
        queryKey: subscriptionKeys.summary(),
      });

      void queryClient.invalidateQueries({
        queryKey: subscriptionKeys.usage(),
      });
    },
  });
}

export function useCancelSubscription() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: {
      payload: CancelSubscriptionRequest;
      idempotencyKey?: string;
    }) =>
      subscriptionsApi.cancelSubscription(
        variables.payload,
        variables.idempotencyKey,
      ),

    onSuccess: (subscription) => {
      queryClient.setQueryData(
        subscriptionKeys.current(),
        subscription,
      );

      void queryClient.invalidateQueries({
        queryKey: subscriptionKeys.summary(),
      });

      void queryClient.invalidateQueries({
        queryKey: subscriptionKeys.usage(),
      });
    },
  });
}

export function useAdminSubscriptions(
  params: AdminSubscriptionListParams = {},
) {
  return useQuery({
    queryKey: subscriptionKeys.admin(params),
    queryFn: () => subscriptionsApi.listAllSubscriptions(params),
  });
}