import React, { useCallback, useEffect, useMemo, useState } from "react";
import {ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";
import { useRouter } from "expo-router";
import {listSubscriptionPlans, getSubscriptionSummary, getSubscriptionUsage, changeSubscriptionPlan, cancelSubscription, reactivateSubscription,
} from "../../../api/subscriptions";
import type {Plan, Subscription,  SubscriptionSummary,Usage, UsageMetric, BillingInterval, ChangePlanPayload, CancelSubscriptionPayload,
} from "../../../api/types";
import { restoreSession } from "../../../api/client";
import type { AuthUser } from "../../../api/types";

const PERM = {
  READ: "subscription.read",
  MANAGE: "subscription.manage",
  BILLING: "subscription.billing.manage",
} as const;

function useSubscriptionPermissions() {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const u = await restoreSession();
        if (!cancelled) setUser(u);
      } catch {
        if (!cancelled) setUser(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const keys = useMemo(() => {
    const perms = user?.role?.permissions ?? [];
    return new Set(
      perms.map((p) => (p.key?.toLowerCase?.() ?? String(p.key)) as string)
    );
  }, [user]);

  const has = (key: string) => {
    const lower = key.toLowerCase();
    const upperSnake = key.toUpperCase().replace(/\./g, "_");
    return keys.has(lower) || keys.has(upperSnake) || keys.has(key);
  };

  return {
    canRead: has("subscription.read") || has("SUBSCRIPTION_READ"),
    canManage: has("subscription.manage") || has("SUBSCRIPTION_MANAGE"),
    canBilling:
      has("subscription.billing.manage") || has("SUBSCRIPTION_BILLING_MANAGE"),
  };
}

function formatMoney(amount: string | number | null | undefined, currency = "PKR"): string {
  if (amount == null) return "—";
  const n = typeof amount === "string" ? parseFloat(amount) : amount;
  if (Number.isNaN(n)) return String(amount);
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `${currency} ${n.toLocaleString()}`;
  }
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "Unlimited";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const val = bytes / Math.pow(1024, i);
  return `${val < 10 ? val.toFixed(1) : Math.round(val)} ${units[i]}`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function metricLabel(metric: string): string {
  const labels: Record<string, string> = {
    storage_bytes: "Storage",
    drawings: "Drawings",
    projects: "Projects",
    ai_requests: "AI requests",
    site_photos: "Site photos",
  };
  return labels[metric] ?? metric.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(metric: string, value: number | null): string {
  if (value == null) return "Unlimited";
  if (metric === "storage_bytes") return formatBytes(value);
  return value.toLocaleString();
}

function statusColor(status: string): string {
  switch (status) {
    case "ACTIVE":
    case "TRIALING":
      return "#16a34a";
    case "PAST_DUE":
      return "#ca8a04";
    case "CANCELLED":
    case "EXPIRED":
      return "#dc2626";
    default:
      return "#64748b";
  }
}

function extractErrorMessage(err: unknown): string {
  if (!err || typeof err !== "object") return "Something went wrong.";
  const e = err as {
    message?: string;
    detail?: string | Array<{ msg?: string }>;
    body?: { detail?: string | Array<{ msg?: string }>; message?: string };
    status?: number;
    statusCode?: number;
  };
  const body = e.body ?? e;
  const detail = body.detail ?? body.message ?? e.message;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg!;
  return "Something went wrong.";
}

export default function SubscriptionScreen() {
  const router = useRouter();
  const { canRead, canManage, canBilling } = useSubscriptionPermissions();

  const [plans, setPlans] = useState<Plan[]>([]);
  const [summary, setSummary] = useState<SubscriptionSummary | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subscriptionNotFound, setSubscriptionNotFound] = useState(false);

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [billingInterval, setBillingInterval] = useState<BillingInterval>("MONTHLY");
  const [quantity, setQuantity] = useState("1");

  const [showCancelForm, setShowCancelForm] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelFeedback, setCancelFeedback] = useState("");
  const [cancelImmediate, setCancelImmediate] = useState(false);

  const loadData = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      setSubscriptionNotFound(false);

      try {
        const planList = await listSubscriptionPlans();
        setPlans([...planList].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)));

        if (canRead) {
          try {
            const [sum, usg] = await Promise.all([
              getSubscriptionSummary(),
              getSubscriptionUsage(),
            ]);
            setSummary(sum);
            setUsage(usg);
            setSelectedPlanId(sum.subscription.plan_id);
            setBillingInterval(sum.subscription.billing_interval);
            setQuantity(String(sum.subscription.quantity || 1));
          } catch (subErr: unknown) {
            const msg = extractErrorMessage(subErr);
            const status =
              (subErr as { status?: number; statusCode?: number })?.status ??
              (subErr as { status?: number; statusCode?: number })?.statusCode;
            if (
              status === 404 ||
              /not found/i.test(msg) ||
              /SUBSCRIPTION_NOT_FOUND/i.test(msg)
            ) {
              setSubscriptionNotFound(true);
              setSummary(null);
              setUsage(null);
            } else if (status === 403) {
              setError("You do not have permission to view subscription details.");
            } else {
              setError(msg);
            }
          }
        }
      } catch (err: unknown) {
        setError(extractErrorMessage(err));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [canRead]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleChangePlan = async () => {
    if (!canManage) {
      Alert.alert("Permission denied", "You need subscription.manage to change plans.");
      return;
    }
    if (!selectedPlanId) {
      Alert.alert("Select a plan", "Please select a plan first.");
      return;
    }
    const qty = Math.max(1, parseInt(quantity, 10) || 1);
    const payload: ChangePlanPayload = {
      plan_id: selectedPlanId,
      billing_interval: billingInterval,
      quantity: qty,
    };

    setActionLoading(true);
    try {
      await changeSubscriptionPlan(payload, `change-plan-${Date.now()}`);
      Alert.alert("Success", "Subscription plan updated.");
      await loadData(true);
    } catch (err: unknown) {
      Alert.alert("Unable to change plan", extractErrorMessage(err));
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!canBilling) {
      Alert.alert("Permission denied", "You need subscription.billing.manage to cancel.");
      return;
    }

    const confirmTitle = cancelImmediate ? "Cancel immediately?" : "Schedule cancellation?";
    const confirmMsg = cancelImmediate
      ? "This cancels right away. Access ends immediately."
      : "Cancellation takes effect at the end of the current billing period. You keep access until then.";

    Alert.alert(confirmTitle, confirmMsg, [
      { text: "Back", style: "cancel" },
      {
        text: cancelImmediate ? "Cancel now" : "Schedule cancellation",
        style: "destructive",
        onPress: async () => {
          setActionLoading(true);
          try {
            const payload: CancelSubscriptionPayload = {
              cancel_at_period_end: !cancelImmediate,
              reason: cancelReason.trim() || null,
              feedback: cancelFeedback.trim() || null,
            };
            await cancelSubscription(payload, `cancel-${Date.now()}`);
            Alert.alert(
              "Done",
              cancelImmediate
                ? "Subscription cancelled."
                : "Cancellation scheduled for end of period."
            );
            setShowCancelForm(false);
            setCancelReason("");
            setCancelFeedback("");
            setCancelImmediate(false);
            await loadData(true);
          } catch (err: unknown) {
            Alert.alert("Unable to cancel", extractErrorMessage(err));
          } finally {
            setActionLoading(false);
          }
        },
      },
    ]);
  };

  const handleReactivate = async () => {
    if (!canBilling) {
      Alert.alert("Permission denied", "You need subscription.billing.manage to reactivate.");
      return;
    }
    setActionLoading(true);
    try {
      await reactivateSubscription();
      Alert.alert("Success", "Subscription reactivated.");
      await loadData(true);
    } catch (err: unknown) {
      Alert.alert("Unable to reactivate", extractErrorMessage(err));
    } finally {
      setActionLoading(false);
    }
  };

  const subscription: Subscription | null = summary?.subscription ?? null;
  const currentPlan: Plan | null = summary?.plan ?? null;
  const canReactivate =
    !!subscription &&
    subscription.cancel_at_period_end &&
    !["CANCELLED", "EXPIRED"].includes(subscription.status);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0f172a" />
        <Text style={styles.muted}>Loading subscription…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => loadData(true)} />
      }
    >
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Text style={styles.back}>← Back</Text>
        </Pressable>
        <Text style={styles.title}>Subscription</Text>
        <Text style={styles.subtitle}>Plans, usage, and billing for your organization</Text>
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={() => loadData()}>
            <Text style={styles.retryBtnText}>Retry</Text>
          </Pressable>
        </View>
      ) : null}

      <Section title="Current subscription">
        {subscriptionNotFound ? (
          <Text style={styles.muted}>
            No subscription found for this organization. Plans are still available below
            {canManage ? " — you can select one to get started." : "."}
          </Text>
        ) : !canRead ? (
          <Text style={styles.muted}>You do not have permission to view subscription details.</Text>
        ) : !subscription ? (
          <Text style={styles.muted}>No subscription data.</Text>
        ) : (
          <View style={styles.card}>
            <Row label="Plan" value={currentPlan?.name ?? subscription.plan_id} />
            <Row
              label="Status"
              value={
                <Text
                  style={[
                    styles.badge,
                    {
                      backgroundColor: statusColor(subscription.status) + "22",
                      color: statusColor(subscription.status),
                    },
                  ]}
                >
                  {subscription.status}
                </Text>
              }
            />
            <Row label="Billing interval" value={subscription.billing_interval} />
            <Row label="Quantity" value={String(subscription.quantity)} />
            <Row
              label="Period"
              value={`${formatDate(subscription.current_period_start)} → ${formatDate(subscription.current_period_end)}`}
            />
            {subscription.trial_ends_at ? (
              <Row label="Trial ends" value={formatDate(subscription.trial_ends_at)} />
            ) : null}
            {subscription.next_billing_at ? (
              <Row label="Next billing" value={formatDate(subscription.next_billing_at)} />
            ) : null}
            {subscription.cancel_at_period_end ? (
              <View style={styles.notice}>
                <Text style={styles.noticeText}>
                  Cancellation is scheduled for the end of the current period (
                  {formatDate(subscription.current_period_end)}).
                </Text>
              </View>
            ) : null}
            {subscription.cancellation_reason ? (
              <Row label="Cancel reason" value={subscription.cancellation_reason} />
            ) : null}
          </View>
        )}
      </Section>

      <Section title="Plans">
        {plans.length === 0 ? (
          <Text style={styles.muted}>No public plans available.</Text>
        ) : (
          plans.map((plan) => {
            const isSelected = selectedPlanId === plan.id;
            const isCurrent = subscription?.plan_id === plan.id;
            return (
              <Pressable
                key={plan.id}
                style={[
                  styles.planCard,
                  isSelected && styles.planCardSelected,
                  isCurrent && styles.planCardCurrent,
                ]}
                onPress={() => {
                  if (canManage) setSelectedPlanId(plan.id);
                }}
                disabled={!canManage || actionLoading}
              >
                <View style={styles.planHeader}>
                  <Text style={styles.planName}>
                    {plan.name}
                    {isCurrent ? "  · current" : ""}
                  </Text>
                  {plan.offer_label ? (
                    <Text style={styles.offerBadge}>{plan.offer_label}</Text>
                  ) : null}
                </View>
                {plan.description ? (
                  <Text style={styles.planDesc}>{plan.description}</Text>
                ) : null}

                <View style={styles.priceRow}>
                  <PriceLine
                    label="Monthly"
                    price={plan.price_monthly}
                    original={plan.price_monthly_original}
                    currency={plan.currency}
                  />
                  <PriceLine
                    label="Yearly"
                    price={plan.price_yearly}
                    original={plan.price_yearly_original}
                    currency={plan.currency}
                  />
                </View>

                {plan.offer_ends_at ? (
                  <Text style={styles.mutedSmall}>Offer ends {formatDate(plan.offer_ends_at)}</Text>
                ) : null}
                {plan.trial_days > 0 ? (
                  <Text style={styles.mutedSmall}>{plan.trial_days}-day trial</Text>
                ) : null}

                {plan.features && Object.keys(plan.features).length > 0 ? (
                  <View style={styles.chipRow}>
                    {Object.entries(plan.features).map(([k, v]) =>
                      v ? (
                        <View key={k} style={styles.chip}>
                          <Text style={styles.chipText}>{k.replace(/_/g, " ")}</Text>
                        </View>
                      ) : null
                    )}
                  </View>
                ) : null}

                {plan.quotas && Object.keys(plan.quotas).length > 0 ? (
                  <View style={styles.quotaBlock}>
                    {Object.entries(plan.quotas).map(([metric, limit]) => (
                      <Text key={metric} style={styles.quotaLine}>
                        {metricLabel(metric)}:{" "}
                        {formatMetricValue(metric, limit as number | null)}
                        {plan.limit_policy?.[metric]
                          ? ` (${plan.limit_policy[metric]})`
                          : ""}
                      </Text>
                    ))}
                  </View>
                ) : null}
              </Pressable>
            );
          })
        )}

        {canManage && plans.length > 0 ? (
          <View style={styles.formCard}>
            <Text style={styles.formTitle}>Change plan</Text>

            <Text style={styles.label}>Billing interval</Text>
            <View style={styles.segment}>
              {(["MONTHLY", "YEARLY"] as BillingInterval[]).map((iv) => (
                <Pressable
                  key={iv}
                  style={[styles.segmentBtn, billingInterval === iv && styles.segmentBtnActive]}
                  onPress={() => setBillingInterval(iv)}
                  disabled={actionLoading}
                >
                  <Text
                    style={[
                      styles.segmentText,
                      billingInterval === iv && styles.segmentTextActive,
                    ]}
                  >
                    {iv === "MONTHLY" ? "Monthly" : "Yearly"}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>Quantity</Text>
            <TextInput
              style={styles.input}
              value={quantity}
              onChangeText={setQuantity}
              keyboardType="number-pad"
              editable={!actionLoading}
            />

            <Pressable
              style={[
                styles.primaryBtn,
                (actionLoading || !selectedPlanId) && styles.btnDisabled,
              ]}
              onPress={handleChangePlan}
              disabled={actionLoading || !selectedPlanId}
            >
              {actionLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>Update plan</Text>
              )}
            </Pressable>
            <Text style={styles.hint}>
              Sends plan_id, billing_interval, and quantity. No checkout or invoice is started by
              this endpoint.
            </Text>
          </View>
        ) : null}
      </Section>

      {canRead ? (
        <Section title="Usage">
          {!usage ? (
            <Text style={styles.muted}>
              {subscriptionNotFound
                ? "Usage is unavailable without a subscription."
                : "No usage data."}
            </Text>
          ) : (
            <View style={styles.card}>
              <Text style={styles.mutedSmall}>
                Period: {formatDate(usage.period_start)} → {formatDate(usage.period_end)}
              </Text>
              {usage.metrics.length === 0 ? (
                <Text style={styles.muted}>No metrics for this period.</Text>
              ) : (
                usage.metrics.map((m: UsageMetric) => <UsageRow key={m.metric} metric={m} />)
              )}
            </View>
          )}
        </Section>
      ) : null}

      {canBilling && subscription && !subscriptionNotFound ? (
        <Section title="Billing actions">
          {canReactivate ? (
            <Pressable
              style={[styles.secondaryBtn, actionLoading && styles.btnDisabled]}
              onPress={handleReactivate}
              disabled={actionLoading}
            >
              <Text style={styles.secondaryBtnText}>Reactivate subscription</Text>
            </Pressable>
          ) : null}

          {!subscription.cancel_at_period_end &&
          !["CANCELLED", "EXPIRED"].includes(subscription.status) ? (
            <>
              {!showCancelForm ? (
                <Pressable
                  style={styles.dangerOutlineBtn}
                  onPress={() => setShowCancelForm(true)}
                  disabled={actionLoading}
                >
                  <Text style={styles.dangerOutlineText}>Cancel subscription…</Text>
                </Pressable>
              ) : (
                <View style={styles.formCard}>
                  <Text style={styles.formTitle}>Cancel subscription</Text>

                  <Text style={styles.label}>Reason (optional)</Text>
                  <TextInput
                    style={styles.input}
                    value={cancelReason}
                    onChangeText={setCancelReason}
                    placeholder="Why are you cancelling?"
                    editable={!actionLoading}
                  />

                  <Text style={styles.label}>Feedback (optional)</Text>
                  <TextInput
                    style={[styles.input, styles.textArea]}
                    value={cancelFeedback}
                    onChangeText={setCancelFeedback}
                    placeholder="Any additional feedback"
                    multiline
                    numberOfLines={3}
                    editable={!actionLoading}
                  />

                  <Pressable
                    style={styles.checkRow}
                    onPress={() => setCancelImmediate((v) => !v)}
                    disabled={actionLoading}
                  >
                    <View
                      style={[styles.checkbox, cancelImmediate && styles.checkboxChecked]}
                    />
                    <Text style={styles.checkLabel}>
                      Cancel immediately (instead of at period end)
                    </Text>
                  </Pressable>

                  <Text style={styles.hint}>
                    Default is schedule cancellation for end of period (cancel_at_period_end:
                    true). Immediate sets it to false and ends access now.
                  </Text>

                  <View style={styles.rowBtns}>
                    <Pressable
                      style={styles.ghostBtn}
                      onPress={() => {
                        setShowCancelForm(false);
                        setCancelImmediate(false);
                      }}
                      disabled={actionLoading}
                    >
                      <Text style={styles.ghostBtnText}>Back</Text>
                    </Pressable>
                    <Pressable
                      style={[styles.dangerBtn, actionLoading && styles.btnDisabled]}
                      onPress={handleCancel}
                      disabled={actionLoading}
                    >
                      {actionLoading ? (
                        <ActivityIndicator color="#fff" />
                      ) : (
                        <Text style={styles.dangerBtnText}>
                          {cancelImmediate ? "Cancel now" : "Schedule cancellation"}
                        </Text>
                      )}
                    </Pressable>
                  </View>
                </View>
              )}
            </>
          ) : null}
        </Section>
      ) : null}

      <View style={{ height: 48 }} />
    </ScrollView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      {typeof value === "string" || typeof value === "number" ? (
        <Text style={styles.rowValue}>{value}</Text>
      ) : (
        value
      )}
    </View>
  );
}

function PriceLine({
  label,
  price,
  original,
  currency,
}: {
  label: string;
  price: string | number;
  original: string | number | null;
  currency: string;
}) {
  const hasOffer =
    original != null && parseFloat(String(original)) > parseFloat(String(price));
  return (
    <View style={styles.priceLine}>
      <Text style={styles.priceLabel}>{label}</Text>
      <Text style={styles.priceValue}>
        {formatMoney(price, currency)}
        {hasOffer ? (
          <Text style={styles.priceOriginal}> {formatMoney(original, currency)}</Text>
        ) : null}
      </Text>
    </View>
  );
}

function UsageRow({ metric }: { metric: UsageMetric }) {
  const isUnlimited = metric.limit == null;
  const pct =
    metric.percentage != null ? Math.min(100, Math.max(0, metric.percentage)) : null;

  return (
    <View style={styles.usageRow}>
      <View style={styles.usageHeader}>
        <Text style={styles.usageName}>{metricLabel(metric.metric)}</Text>
        <Text style={styles.usageNums}>
          {formatMetricValue(metric.metric, metric.used)}
          {" / "}
          {isUnlimited ? "Unlimited" : formatMetricValue(metric.metric, metric.limit)}
        </Text>
      </View>
      {!isUnlimited && pct != null ? (
        <>
          <View style={styles.barTrack}>
            <View
              style={[
                styles.barFill,
                {
                  width: `${pct}%`,
                  backgroundColor: pct >= 100 ? "#dc2626" : pct >= 80 ? "#ca8a04" : "#16a34a",
                },
              ]}
            />
          </View>
          <Text style={styles.mutedSmall}>
            {metric.remaining != null
              ? `${formatMetricValue(metric.metric, metric.remaining)} remaining`
              : `${pct.toFixed(0)}% used`}
          </Text>
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 32 },
  centered: {flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#f8fafc", gap: 12,},
  header: { marginBottom: 16 },
  back: { color: "#0f172a", fontSize: 15, marginBottom: 8 },
  title: { fontSize: 24, fontWeight: "700", color: "#0f172a" },
  subtitle: { fontSize: 14, color: "#64748b", marginTop: 4 },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#0f172a", marginBottom: 10 },
  card: {backgroundColor: "#fff", borderRadius: 12, padding: 14, borderWidth: 1, borderColor: "#e2e8f0", gap: 8,},
  row: {flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12,},
  rowLabel: { fontSize: 13, color: "#64748b", flexShrink: 0 },
  rowValue: {fontSize: 14, color: "#0f172a", fontWeight: "500", flex: 1, textAlign: "right",},
  badge: {fontSize: 12, fontWeight: "700", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6, overflow: "hidden",},
  notice: {backgroundColor: "#fef3c7", borderRadius: 8, padding: 10, marginTop: 4,},
  noticeText: { color: "#92400e", fontSize: 13 },
  planCard: {backgroundColor: "#fff", borderRadius: 12, padding: 14, borderWidth: 1.5, borderColor: "#e2e8f0", marginBottom: 10,},
  planCardSelected: { borderColor: "#0f172a" },
  planCardCurrent: { backgroundColor: "#f1f5f9" },
  planHeader: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8,},
  planName: { fontSize: 17, fontWeight: "700", color: "#0f172a" },
  planDesc: { fontSize: 13, color: "#64748b", marginTop: 4 },
  offerBadge: {backgroundColor: "#dcfce7", color: "#166534", fontSize: 11, fontWeight: "700", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6, overflow: "hidden",},
  priceRow: { flexDirection: "row", gap: 16, marginTop: 10 },
  priceLine: { flex: 1 },
  priceLabel: { fontSize: 12, color: "#64748b" },
  priceValue: { fontSize: 15, fontWeight: "600", color: "#0f172a" },
  priceOriginal: {fontSize: 12, color: "#94a3b8", textDecorationLine: "line-through", fontWeight: "400",},
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 10 },
  chip: {backgroundColor: "#e2e8f0", borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3,},
  chipText: { fontSize: 11, color: "#334155", textTransform: "capitalize" },
  quotaBlock: { marginTop: 8, gap: 2 },
  quotaLine: { fontSize: 12, color: "#475569" },
  formCard: {backgroundColor: "#fff", borderRadius: 12, padding: 14, borderWidth: 1, borderColor: "#e2e8f0", marginTop: 8, gap: 8,},
  formTitle: { fontSize: 15, fontWeight: "700", color: "#0f172a", marginBottom: 4 },
  label: { fontSize: 13, color: "#64748b", marginTop: 4 },
  input: {borderWidth: 1, borderColor: "#cbd5e1", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, color: "#0f172a", backgroundColor: "#fff",},
  textArea: { minHeight: 72, textAlignVertical: "top" },
  segment: { flexDirection: "row", gap: 8 },
  segmentBtn: {flex: 1, paddingVertical: 10, borderRadius: 8, borderWidth: 1, borderColor: "#cbd5e1", alignItems: "center",},
  segmentBtnActive: { backgroundColor: "#0f172a", borderColor: "#0f172a" },
  segmentText: { fontSize: 14, color: "#0f172a", fontWeight: "600" },
  segmentTextActive: { color: "#fff" },
  primaryBtn: {backgroundColor: "#0f172a", borderRadius: 10, paddingVertical: 14, alignItems: "center", marginTop: 8,},
  primaryBtnText: { color: "#fff", fontSize: 15, fontWeight: "700" },
  secondaryBtn: {backgroundColor: "#fff", borderRadius: 10, paddingVertical: 14, alignItems: "center", borderWidth: 1.5, borderColor: "#0f172a", marginBottom: 10,},
  secondaryBtnText: { color: "#0f172a", fontSize: 15, fontWeight: "700" },
  dangerBtn: {backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 14, paddingHorizontal: 16, alignItems: "center", flex: 1,},
  dangerBtnText: { color: "#fff", fontSize: 15, fontWeight: "700" },
  dangerOutlineBtn: {borderRadius: 10, paddingVertical: 14, alignItems: "center", borderWidth: 1.5, borderColor: "#dc2626",},
  dangerOutlineText: { color: "#dc2626", fontSize: 15, fontWeight: "700" },
  ghostBtn: {borderRadius: 10, paddingVertical: 14, paddingHorizontal: 16, alignItems: "center", borderWidth: 1, borderColor: "#cbd5e1",},
  ghostBtnText: { color: "#64748b", fontSize: 15, fontWeight: "600" },
  btnDisabled: { opacity: 0.5 },
  rowBtns: { flexDirection: "row", gap: 10, marginTop: 8 },
  checkRow: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 8 },
  checkbox: {width: 20, height: 20, borderRadius: 4, borderWidth: 1.5, borderColor: "#94a3b8",},
  checkboxChecked: { backgroundColor: "#0f172a", borderColor: "#0f172a" },
  checkLabel: { flex: 1, fontSize: 13, color: "#334155" },
  hint: { fontSize: 12, color: "#94a3b8", marginTop: 4 },
  muted: { fontSize: 14, color: "#64748b" },
  mutedSmall: { fontSize: 12, color: "#94a3b8", marginTop: 2 },
  usageRow: { marginTop: 12, gap: 4 },
  usageHeader: {flexDirection: "row", justifyContent: "space-between", alignItems: "center",},
  usageName: { fontSize: 14, fontWeight: "600", color: "#0f172a" },
  usageNums: { fontSize: 13, color: "#475569" },
  barTrack: {height: 6, backgroundColor: "#e2e8f0", borderRadius: 3, overflow: "hidden",},
  barFill: { height: 6, borderRadius: 3 },
  errorBox: {backgroundColor: "#fef2f2", borderRadius: 10, padding: 12, marginBottom: 16, borderWidth: 1, borderColor: "#fecaca",},
  errorText: { color: "#b91c1c", fontSize: 14 },
  retryBtn: { marginTop: 8, alignSelf: "flex-start", paddingVertical: 6, paddingHorizontal: 12, backgroundColor: "#fff", borderRadius: 6, borderWidth: 1, borderColor: "#fecaca",},
  retryBtnText: { color: "#b91c1c", fontWeight: "600", fontSize: 13 },
});