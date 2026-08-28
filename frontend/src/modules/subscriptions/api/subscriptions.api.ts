import { apiClient } from "../../../shared/api/client";
import type {CancelSubscriptionRequest, ChangePlanRequest, Plan, Subscription, UsageResponse,
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

  async getUsage(): Promise<UsageResponse> {
    const response = await apiClient.get<UsageResponse>(
      "/subscriptions/me/usage",
    );

    return response.data;
  },

  async changePlan(
    payload: ChangePlanRequest,
  ): Promise<Subscription> {
    const response = await apiClient.patch<Subscription>(
      "/subscriptions/me/plan",
      payload,
    );

    return response.data;
  },

  async cancelSubscription(
    payload: CancelSubscriptionRequest,
  ): Promise<Subscription> {
    const response = await apiClient.post<Subscription>(
      "/subscriptions/me/cancel",
      payload,
    );

    return response.data;
  },
};