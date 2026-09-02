import { apiClient } from "../../../shared/api/client";
import type {
  AdminSubscriptionListParams, CancelSubscriptionRequest, ChangePlanRequest, Plan,
  Subscription, SubscriptionListResponse, SubscriptionSummary, UsageResponse,
} from "../types/subscription.types";

export const subscriptionsApi = {
  async listPlans(): Promise<Plan[]> {
    const response = await apiClient.get<Plan[]>(
      "/subscriptions/plans",
    );

    return response.data;
  },

  async getSubscription(): Promise<Subscription> {
    const response = await apiClient.get<Subscription>(
      "/subscriptions/me",
    );
    return response.data;
  },

  async getSubscriptionSummary(): Promise<SubscriptionSummary> {
    const response = await apiClient.get<SubscriptionSummary>(
      "/subscriptions/me/summary",
    );
    return response.data;
  },

  async getUsage(): Promise<UsageResponse> {
    const response = await apiClient.get<UsageResponse>(
      "/subscriptions/me/usage",
    );

    return response.data;
  },

    async changePlan(
    payload: ChangePlanRequest,
    idempotencyKey?: string,
  ): Promise<Subscription> {
    const response = await apiClient.patch<Subscription>(
      "/subscriptions/me/plan",
      payload,
      idempotencyKey
        ? { headers: { "Idempotency-Key": idempotencyKey } }
        : undefined,
    );

    return response.data;
  },

  async cancelSubscription(
    payload: CancelSubscriptionRequest,
    idempotencyKey?: string,
  ): Promise<Subscription> {
    const response = await apiClient.post<Subscription>(
      "/subscriptions/me/cancel",
      payload,
      idempotencyKey
        ? { headers: { "Idempotency-Key": idempotencyKey } }
        : undefined,
    );
    return response.data;
  },

  async listAllSubscriptions(
    params: AdminSubscriptionListParams = {},
  ): Promise<SubscriptionListResponse> {
    const response = await apiClient.get<SubscriptionListResponse>(
      "/subscriptions/admin",
      { params },
    );

    return response.data;
  },
};