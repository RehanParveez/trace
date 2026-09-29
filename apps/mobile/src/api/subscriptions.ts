import { authenticatedRequest } from "./client";
import type {Plan, Subscription, SubscriptionSummary, Usage, ChangePlanPayload, CancelSubscriptionPayload,
} from "./types";

const BASE = "/subscriptions";

export async function listSubscriptionPlans(): Promise<Plan[]> {
  return authenticatedRequest<Plan[]>(`${BASE}/plans`, { method: "GET" });
}

export async function getSubscriptionSummary(): Promise<SubscriptionSummary> {
  return authenticatedRequest<SubscriptionSummary>(`${BASE}/me/summary`, {
    method: "GET",
  });
}

export async function getSubscription(): Promise<Subscription> {
  return authenticatedRequest<Subscription>(`${BASE}/me`, { method: "GET" });
}

export async function getSubscriptionUsage(): Promise<Usage> {
  return authenticatedRequest<Usage>(`${BASE}/me/usage`, { method: "GET" });
}

export async function changeSubscriptionPlan(
  payload: ChangePlanPayload,
  idempotencyKey?: string
): Promise<Subscription> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  return authenticatedRequest<Subscription>(`${BASE}/me/plan`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(payload),
  });
}

export async function cancelSubscription(
  payload: CancelSubscriptionPayload,
  idempotencyKey?: string
): Promise<Subscription> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  return authenticatedRequest<Subscription>(`${BASE}/me/cancel`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
}

export async function reactivateSubscription(): Promise<Subscription> {
  return authenticatedRequest<Subscription>(`${BASE}/me/reactivate`, {
    method: "POST",
  });
}