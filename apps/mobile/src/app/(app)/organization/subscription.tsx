import { useCallback, useEffect, useState } from "react";
import {ActivityIndicator, Alert, LayoutAnimation, Platform, Pressable, RefreshControl, ScrollView, StyleProp, StyleSheet, Text, TextInput, UIManager, View, ViewStyle,
} from "react-native";
import { Link, router } from "expo-router";
import {cancelSubscription, changeSubscriptionPlan,  getSubscriptionSummary, getSubscriptionUsage, listSubscriptionPlans, reactivateSubscription,
} from "../../../api/subscriptions";
import { restoreSession } from "../../../api/client";
import type {BillingInterval, CancelSubscriptionPayload, ChangePlanPayload, Plan, Subscription, SubscriptionSummary, Usage, UsageMetric,
} from "../../../api/types";
import LanguageSwitcher from "../../../components/LanguageSwitcher";
import i18n from "../../../i18n";
import { useTranslation } from "react-i18next";

const C = {
  background: "#F3EEE4",
  surface: "#FFFFFF",
  navy: "#080D18",
  navySoft: "#18283B",
  text: "#191410",
  secondary: "#5C5347",
  muted: "#8C806E",
  border: "#E4D9C4",
  green: "#24744A",
  greenBg: "#EAF4EC",
  amber: "#8A5A0A",
  amberBg: "#FFF3D8",
  red: "#A33C32",
  redBg: "#FBECE9",
} as const;

const PERMISSION = {
  read: "subscription.read",
  manage: "subscription.manage",
  billing: "subscription.billing.manage",
} as const;

if (
  Platform.OS === "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

function hasPermission(keys: Set<string>, key: string) {
  return (
    keys.has(key) ||
    keys.has(key.toUpperCase().replace(/\./g, "_"))
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "string" && error.trim()) return error;

  if (error && typeof error === "object") {
    const value = error as {
      message?: unknown;
      detail?: unknown;
      body?: { message?: unknown; detail?: unknown };
    };

    const detail = value.body?.detail ?? value.detail;
    const message = value.body?.message ?? value.message;

    if (typeof detail === "string") return detail;
    if (typeof message === "string") return message;

    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : "",
        )
        .filter(Boolean);

      if (messages.length) return messages.join(", ");
    }
  }

  return "Something went wrong. Please try again.";
}

function isNotFoundError(error: unknown, message: string) {
  const status =
    error && typeof error === "object"
      ? (error as { status?: number; statusCode?: number }).status ??
        (error as { statusCode?: number }).statusCode
      : undefined;

  return (
    status === 404 ||
    /\b404\b|not found|subscription_not_found/i.test(message)
  );
}

function formatMoney(
  amount: string | number | null | undefined,
  currency = "PKR",
  locale = i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK",
) {
  if (amount == null) return "—";

  const number =
    typeof amount === "number" ? amount : Number.parseFloat(amount);

  if (!Number.isFinite(number)) return String(amount);

  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(number);
  } catch {
    return `${currency} ${number.toLocaleString()}`;
  }
}

function formatBytes(bytes: number | null) {
  if (bytes == null) return i18n.t("subscription.unlimited");
  if (bytes <= 0) return "0 B";

  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** index;

  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[index]}`;
}

function formatDate(value: string | null | undefined, locale = i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK") {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function metricLabel(metric: string) {
  const labels: Record<string, string> = {
    storage_bytes: i18n.t("subscription.metricStorage"),
    drawings: i18n.t("subscription.metricDrawings"),
    projects: i18n.t("subscription.metricProjects"),
    ai_requests: i18n.t("subscription.metricAIRequests"),
    site_photos: i18n.t("subscription.metricSitePhotos"),
  };

  return (
    labels[metric] ??
    metric.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  );
}

function metricValue(metric: string, value: number | null) {
  if (value == null) return i18n.t("subscription.unlimited");
  if (metric === "storage_bytes") return formatBytes(value);
  return value.toLocaleString();
}

function statusColors(status: string) {
  switch (status) {
    case "ACTIVE":
    case "TRIALING":
      return { text: C.green, background: C.greenBg };
    case "PAST_DUE":
      return { text: C.amber, background: C.amberBg };
    case "CANCELLED":
    case "EXPIRED":
      return { text: C.red, background: C.redBg };
    default:
      return { text: C.secondary, background: "#F1ECE3" };
  }
}

export default function SubscriptionScreen() {
  const { i18n: activeI18n } = useTranslation();
  const isUrdu = activeI18n.resolvedLanguage === "ur";
  const locale = isUrdu ? "ur-PK" : "en-PK";
  const [plans, setPlans] = useState<Plan[]>([]);
  const [summary, setSummary] = useState<SubscriptionSummary | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);

  const [canRead, setCanRead] = useState(false);
  const [canManage, setCanManage] = useState(false);
  const [canManageBilling, setCanManageBilling] = useState(false);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subscriptionNotFound, setSubscriptionNotFound] = useState(false);

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [billingInterval, setBillingInterval] =
    useState<BillingInterval>("MONTHLY");
  const [quantity, setQuantity] = useState("1");
  const [expandedPlanId, setExpandedPlanId] = useState<string | null>(null);
  const [usageExpanded, setUsageExpanded] = useState(false);

  const [cancelFormOpen, setCancelFormOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelFeedback, setCancelFeedback] = useState("");
  const [cancelImmediately, setCancelImmediately] = useState(false);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const user = await restoreSession();

      if (!user) {
        router.replace("/login");
        return;
      }
      const keys = new Set(
        user.role?.permissions?.map((permission) =>
          String(permission.key).toLowerCase(),
        ) ?? [],
      );

      const readAllowed = hasPermission(keys, PERMISSION.read);
      const manageAllowed = hasPermission(keys, PERMISSION.manage);
      const billingAllowed = hasPermission(keys, PERMISSION.billing);

      setCanRead(readAllowed);
      setCanManage(manageAllowed);
      setCanManageBilling(billingAllowed);

      if (!readAllowed && !manageAllowed) {
        setPlans([]);
        setSummary(null);
        setUsage(null);
        setSubscriptionNotFound(false);
        setError(i18n.t("subscription.accessDenied"));
        return;
      }

      const requests: Promise<unknown>[] = [
        listSubscriptionPlans(),
      ];

      if (readAllowed) {
        requests.push(getSubscriptionSummary(), getSubscriptionUsage());
      }

      const results = await Promise.allSettled(requests);
      const planResult = results[0];

      if (planResult.status === "fulfilled") {
        const planRows = planResult.value as Plan[];
        setPlans(
          [...planRows].sort(
            (left, right) =>
              (left.sort_order ?? 0) - (right.sort_order ?? 0),
          ),
        );
      } else {
        setPlans([]);
        setError(getErrorMessage(planResult.reason));
      }

      if (!readAllowed) {
        setSummary(null);
        setUsage(null);
        setSubscriptionNotFound(false);
        return;
      }

      const summaryResult = results[1];
      const usageResult = results[2];

      if (summaryResult.status === "fulfilled") {
        const loadedSummary = summaryResult.value as SubscriptionSummary;
        setSummary(loadedSummary);
        setSelectedPlanId(loadedSummary.subscription.plan_id);
        setBillingInterval(loadedSummary.subscription.billing_interval);
        setQuantity(String(loadedSummary.subscription.quantity || 1));
        setSubscriptionNotFound(false);
      } else {
        const message = getErrorMessage(summaryResult.reason);

        if (isNotFoundError(summaryResult.reason, message)) {
          setSummary(null);
          setSelectedPlanId(null);
          setBillingInterval("MONTHLY");
          setQuantity("1");
          setSubscriptionNotFound(true);
        } else {
          setSummary(null);
          setError((current) => current ?? message);
        }
      }

      if (usageResult.status === "fulfilled") {
        setUsage(usageResult.value as Usage);
      } else {
        const message = getErrorMessage(usageResult.reason);
        setUsage(null);

        if (!isNotFoundError(usageResult.reason, message)) {
          setError((current) => current ?? message);
        }
      }
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const subscription: Subscription | null = summary?.subscription ?? null;
  const currentPlan: Plan | null = summary?.plan ?? null;
  const selectedPlan =
    plans.find((plan) => plan.id === selectedPlanId) ?? null;

  const canReactivate =
    Boolean(subscription?.cancel_at_period_end) &&
    !["CANCELLED", "EXPIRED"].includes(subscription?.status ?? "");

  const canCancel =
    Boolean(subscription) &&
    !subscription?.cancel_at_period_end &&
    !["CANCELLED", "EXPIRED"].includes(subscription?.status ?? "");

  const runAction = async (
    title: string,
    action: () => Promise<unknown>,
    successMessage: string,
  ): Promise<boolean> => {
    setActionLoading(true);
    setError(null);

    try {
      await action();
      Alert.alert(i18n.t("subscription.done"), successMessage);
      await loadData(true);
      return true;
    } catch (actionError) {
      Alert.alert(title, getErrorMessage(actionError));
      return false;
    } finally {
      setActionLoading(false);
    }
  };

  const confirmPlanChange = () => {
    if (!canManage) {
      Alert.alert(
        i18n.t("subscription.permissionRequired"),
        i18n.t("subscription.permissionManagePlan"),
      );
      return;
    }

    if (!selectedPlanId) {
      Alert.alert(i18n.t("subscription.choosePlan"), i18n.t("subscription.choosePlanDescription"));
      return;
    }

    const parsedQuantity = Number(quantity);
    if (
      !Number.isInteger(parsedQuantity) ||
      !Number.isFinite(parsedQuantity) ||
      parsedQuantity < 1
    ) {
      Alert.alert(i18n.t("subscription.checkQuantity"), i18n.t("subscription.quantityValidation"));
      return;
    }

    const payload: ChangePlanPayload = {
      plan_id: selectedPlanId,
      billing_interval: billingInterval,
      quantity: parsedQuantity,
    };

    Alert.alert(
      i18n.t("subscription.confirmPlanChange"),
      `${selectedPlan?.name ?? i18n.t("subscription.selectedPlanFallback")} · ${billingInterval.toLowerCase()} · quantity ${parsedQuantity}`,
      [
        { text: i18n.t("subscription.back"), style: "cancel" },
        {
          text: i18n.t("subscription.updatePlan"),
          onPress: () => {
            void runAction(
              i18n.t("subscription.changePlanError"),
              () =>
                changeSubscriptionPlan(
                  payload,
                  `change-plan-${Date.now()}`,
                ),
              i18n.t("subscription.planUpdated"),
            );
          },
        },
      ],
    );
  };

  const confirmCancellation = () => {
    if (!canManageBilling) {
      Alert.alert(
        i18n.t("subscription.permissionRequired"),
        i18n.t("subscription.cancelPermission"),
      );
      return;
    }

    const immediate = cancelImmediately;
    const title = immediate
      ? i18n.t("subscription.cancelNowTitle")
      : i18n.t("subscription.cancelAtEndTitle");
    const message = immediate
      ? i18n.t("subscription.cancelNowConfirm")
      : i18n.t("subscription.cancelAtEndConfirm");

    Alert.alert(title, message, [
      { text: i18n.t("subscription.keepSubscription"), style: "cancel" },
      {
        text: immediate ? i18n.t("subscription.cancelNow") : i18n.t("subscription.scheduleCancellation"),
        style: "destructive",
        onPress: () => {
          const payload: CancelSubscriptionPayload = {
            cancel_at_period_end: !immediate,
            reason: cancelReason.trim() || null,
            feedback: cancelFeedback.trim() || null,
          };

          void (async () => {
            const succeeded = await runAction(
              i18n.t("subscription.cancelError"),
              () =>
                cancelSubscription(
                  payload,
                  `cancel-${Date.now()}`,
                ),
              immediate
                ? i18n.t("subscription.cancelled")
                : i18n.t("subscription.cancellationScheduledSuccess"),
            );

            if (succeeded) {
              setCancelFormOpen(false);
              setCancelReason("");
              setCancelFeedback("");
              setCancelImmediately(false);
            }
          })();
        },
      },
    ]);
  };

  const confirmReactivation = () => {
    if (!canManageBilling) {
      Alert.alert(
        i18n.t("subscription.permissionRequired"),
        i18n.t("subscription.reactivatePermission"),
      );
      return;
    }

    Alert.alert(
      i18n.t("subscription.reactivateTitle"),
      i18n.t("subscription.reactivateConfirm"),
      [
        { text: i18n.t("subscription.back"), style: "cancel" },
        {
          text: i18n.t("subscription.reactivate"),
          onPress: () => {
            void runAction(
              i18n.t("subscription.reactivateError"),
              reactivateSubscription,
              i18n.t("subscription.reactivateSuccess"),
            );
          },
        },
      ],
    );
  };

  const togglePlanDetails = (planId: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpandedPlanId((current) => (current === planId ? null : planId));
  };

  const toggleUsage = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setUsageExpanded((current) => !current);
  };

  if (loading) {
    return (
      <View style={styles.loadingScreen}>
        <ActivityIndicator size="large" color={C.navy} />
        <Text style={styles.muted}>{i18n.t("subscription.loading")}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.screen, isUrdu && { direction: "rtl" }]} contentContainerStyle={[styles.content, isUrdu && { direction: "rtl" }]}
      keyboardShouldPersistTaps="handled"
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void loadData(true)}
          tintColor={C.navy}
        />
      }
    >
      <View style={styles.topBar}>
        <Link href="/organization" asChild>
          <Pressable style={styles.backLink} accessibilityRole="button">
           <Text style={styles.backText}>‹ {i18n.t("subscription.backOrganization")}</Text>
          </Pressable>
        </Link>

        <LanguageSwitcher />
      </View>

      <Text style={styles.pageTitle}>{i18n.t("subscription.pageTitle")}</Text>

      {error ? (
        <View style={styles.errorCard} accessibilityRole="alert">
          <Text style={styles.errorTitle}>{i18n.t("subscription.loadError")}</Text>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable
            onPress={() => void loadData()}
            disabled={loading || refreshing}
            style={styles.retryButton}
            accessibilityRole="button"
          >
            <Text style={styles.retryText}>{i18n.t("subscription.retry")}</Text>
          </Pressable>
        </View>
      ) : null}

      {!canRead && canManage ? (
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>{i18n.t("subscription.planSelectionAccess")}</Text>
          <Text style={styles.muted}>
            {i18n.t("subscription.planSelectionReadOnly")}
          </Text>
        </View>
      ) : null}

      {canRead ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t("subscription.currentPlan")}</Text>

          {subscriptionNotFound ? (
            <View style={styles.infoCard}>
              <Text style={styles.infoTitle}>{i18n.t("subscription.noSubscriptionTitle")}</Text>
              <Text style={styles.muted}>
                {canManage
                  ? i18n.t("subscription.noSubscriptionManage")
                  : i18n.t("subscription.noSubscriptionReadOnly")}
              </Text>
            </View>
          ) : subscription ? (
            <View style={styles.currentPlanCard}>
              <View style={styles.currentPlanTop}>
                <View style={styles.currentPlanCopy}>
                  <Text style={styles.currentPlanName}>
                    {currentPlan?.name ?? subscription.plan_id}
                  </Text>
                  <Text style={styles.currentPlanSubline}>
                    {subscription.billing_interval === "YEARLY"
                      ? i18n.t("subscription.billingYearly")
                      : i18n.t("subscription.billingMonthly")}
                    {" · "}
                    {subscription.quantity}{" "}
                    {subscription.quantity === 1 ? i18n.t("subscription.seatOne") : i18n.t("subscription.seatMany")}
                  </Text>
                </View>
                <StatusBadge status={subscription.status} dark />
              </View>

              <View style={styles.darkDivider} />

              <SummaryRow
                label={i18n.t("subscription.currentPeriod")}
                value={`${formatDate(subscription.current_period_start, locale)} – ${formatDate(subscription.current_period_end, locale)}`}
                dark
              />

              {subscription.next_billing_at ? (
                <SummaryRow
                  label={i18n.t("subscription.nextBilling")}
                  value={formatDate(subscription.next_billing_at, locale)}
                  dark
                />
              ) : null}

              {subscription.trial_ends_at ? (
                <SummaryRow
                  label={i18n.t("subscription.trialEnds")}
                  value={formatDate(subscription.trial_ends_at, locale)}
                  dark
                />
              ) : null}

              {subscription.grace_period_ends_at ? (
                <SummaryRow
                  label={i18n.t("subscription.gracePeriodEnds")}
                  value={formatDate(subscription.grace_period_ends_at, locale)}
                  dark
                />
              ) : null}

              {subscription.cancel_at_period_end ? (
                <View style={styles.darkNotice}>
                  <Text style={styles.darkNoticeText}>
                    
                    {i18n.t("subscription.cancelScheduled", { date: formatDate(subscription.current_period_end, locale) })}
                  </Text>
                </View>
              ) : null}

              {subscription.cancellation_reason ? (
                <SummaryRow
                  label={i18n.t("subscription.cancellationReason")}
                  value={subscription.cancellation_reason}
                  dark
                />
              ) : null}

              {canManageBilling && canReactivate ? (
                <PrimaryButton
                  label={i18n.t("subscription.reactivate")}
                  loading={actionLoading}
                  onPress={confirmReactivation}
                  style={styles.summaryAction}
                />
              ) : null}
            </View>
          ) : (
            <View style={styles.infoCard}>
              <Text style={styles.muted}>
                {i18n.t("subscription.detailsUnavailable")}
              </Text>
            </View>
          )}
        </View>
      ) : null}

      {plans.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t("subscription.plans")}</Text>

          {plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              selected={selectedPlanId === plan.id}
              current={subscription?.plan_id === plan.id}
              expanded={expandedPlanId === plan.id}
              interval={billingInterval}
              canSelect={canManage}
              disabled={actionLoading}
              onSelect={() => {
                if (canManage) setSelectedPlanId(plan.id);
              }}
              onToggleDetails={() => togglePlanDetails(plan.id)}
            />
          ))}

          {canManage ? (
            <View style={styles.actionCard}>
              <Text style={styles.actionCardTitle}>{i18n.t("subscription.changePlan")}</Text>
              <Text style={styles.actionCardDescription}>
                {selectedPlan
                  ? `${selectedPlan.name} · ${billingInterval.toLowerCase()}`
                  : i18n.t("subscription.planSelectHint")}
              </Text>

              <Text style={styles.fieldLabel}>{i18n.t("subscription.billingInterval")}</Text>
              <View style={styles.segment}>
                {(["MONTHLY", "YEARLY"] as BillingInterval[]).map((interval) => {
                  const selected = billingInterval === interval;

                  return (
                    <Pressable
                      key={interval}
                      onPress={() => setBillingInterval(interval)}
                      disabled={actionLoading}
                      accessibilityRole="button"
                      accessibilityState={{ selected }}
                      style={[
                        styles.segmentButton,
                        selected && styles.segmentButtonSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.segmentText,
                          selected && styles.segmentTextSelected,
                        ]}
                      >
                        {interval === "MONTHLY" ? i18n.t("subscription.billingMonthly") : i18n.t("subscription.billingYearly")}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>

              <Text style={styles.fieldLabel}>{i18n.t("subscription.quantity")}</Text>
              <TextInput
                style={styles.input}
                value={quantity}
                onChangeText={(value) =>
                  setQuantity(value.replace(/[^\d]/g, ""))
                }
                keyboardType="number-pad"
                editable={!actionLoading}
                placeholder="1"
                placeholderTextColor={C.muted}
                accessibilityLabel={i18n.t("subscription.quantity")}
              />

              <PrimaryButton
                label={i18n.t("subscription.reviewUpdatePlan")}
                loading={actionLoading}
                disabled={!selectedPlanId || !quantity}
                onPress={confirmPlanChange}
              />
            </View>
          ) : null}
        </View>
      ) : !error ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t("subscription.plans")}</Text>
          <View style={styles.infoCard}>
            <Text style={styles.muted}>{i18n.t("subscription.noPublicPlans")}</Text>
          </View>
        </View>
      ) : null}

      {canRead ? (
        <View style={styles.section}>
          <Pressable
            onPress={toggleUsage}
            style={styles.accordionHeader}
            accessibilityRole="button"
            accessibilityState={{ expanded: usageExpanded }}
          >
            <View style={styles.accordionCopy}>
              <Text style={styles.sectionTitle}>{i18n.t("subscription.usage")}</Text>
              {usage ? (
                <Text style={styles.sectionSubtitle}>
                  {formatDate(usage.period_start, locale)} – {formatDate(usage.period_end, locale)}
                </Text>
              ) : null}
            </View>
            <Text style={styles.accordionIcon}>
              {usageExpanded ? "⌃" : "›"}
            </Text>
          </Pressable>

          {usageExpanded ? (
            !usage ? (
              <View style={styles.infoCard}>
                <Text style={styles.muted}>
                  {subscriptionNotFound
                    ? i18n.t("subscription.usageAfterSubscription")
                    : i18n.t("subscription.noUsage")}
                </Text>
              </View>
            ) : usage.metrics.length === 0 ? (
              <View style={styles.infoCard}>
                <Text style={styles.muted}>{i18n.t("subscription.noUsageMetrics")}</Text>
              </View>
            ) : (
              <View style={styles.usageCard}>
                {usage.metrics.map((metric) => (
                  <UsageRow key={metric.metric} metric={metric} />
                ))}
              </View>
            )
          ) : null}
        </View>
      ) : null}

      {canManageBilling && subscription ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t("subscription.billingActions")}</Text>

          {canCancel ? (
            <View style={styles.actionCard}>
              <Text style={styles.actionCardTitle}>{i18n.t("subscription.cancelSubscription")}</Text>

              {!cancelFormOpen ? (
                <SecondaryButton
                  label={i18n.t("subscription.reviewCancellation")}
                  onPress={() => setCancelFormOpen(true)}
                  disabled={actionLoading}
                />
              ) : (
                <>
                  <Text style={styles.fieldLabel}>{i18n.t("subscription.cancelWhen")}</Text>
                  <View style={styles.segment}>
                    <Pressable
                      onPress={() => setCancelImmediately(false)}
                      accessibilityRole="button"
                      accessibilityState={{ selected: !cancelImmediately }}
                      style={[
                        styles.segmentButton,
                        !cancelImmediately && styles.segmentButtonSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.segmentText,
                          !cancelImmediately && styles.segmentTextSelected,
                        ]}
                      >
                        At period end
                      </Text>
                    </Pressable>

                    <Pressable
                      onPress={() => setCancelImmediately(true)}
                      accessibilityRole="button"
                      accessibilityState={{ selected: cancelImmediately }}
                      style={[
                        styles.segmentButton,
                        cancelImmediately && styles.segmentButtonSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.segmentText,
                          cancelImmediately && styles.segmentTextSelected,
                        ]}
                      >
                        Immediately
                      </Text>
                    </Pressable>
                  </View>

                  <Text style={styles.fieldLabel}>{i18n.t("subscription.cancelReason")}</Text>
                  <TextInput
                    style={styles.input}
                    value={cancelReason}
                    onChangeText={setCancelReason}
                    editable={!actionLoading}
                    placeholder={i18n.t("subscription.cancelReasonPlaceholder")}
                    placeholderTextColor={C.muted}
                  />

                  <Text style={styles.fieldLabel}>{i18n.t("subscription.cancelFeedback")}</Text>
                  <TextInput
                    style={[styles.input, styles.textArea]}
                    value={cancelFeedback}
                    onChangeText={setCancelFeedback}
                    editable={!actionLoading}
                    placeholder={i18n.t("subscription.cancelFeedbackPlaceholder")}
                    placeholderTextColor={C.muted}
                    multiline
                    textAlignVertical="top"
                  />

                  <View style={styles.warningCard}>
                    <Text style={styles.warningText}>
                      {cancelImmediately
                        ? i18n.t("subscription.immediateWarning")
                        : i18n.t("subscription.periodEndWarning", { date: formatDate(subscription.current_period_end, locale) })}
                    </Text>
                  </View>

                  <PrimaryButton
                    label={
                      cancelImmediately
                        ? i18n.t("subscription.continueCancelNow")
                        : "Schedule cancellation"
                    }
                    loading={actionLoading}
                    danger
                    onPress={confirmCancellation}
                  />

                  <SecondaryButton
                    label={i18n.t("subscription.keepSubscription")}
                    onPress={() => {
                      setCancelFormOpen(false);
                      setCancelImmediately(false);
                    }}
                    disabled={actionLoading}
                  />
                </>
              )}
            </View>
          ) : subscription.cancel_at_period_end ? (
            <View style={styles.infoCard}>
              <Text style={styles.infoTitle}>{i18n.t("subscription.cancellationScheduledTitle")}</Text>
              {canReactivate ? (
                <SecondaryButton
                  label={i18n.t("subscription.reactivate")}
                  onPress={confirmReactivation}
                  disabled={actionLoading}
                />
              ) : null}
            </View>
          ) : null}
        </View>
      ) : null}

      {(refreshing || actionLoading) && !loading ? (
        <View style={styles.progressRow}>
          <ActivityIndicator size="small" color={C.navy} />
          <Text style={styles.progressText}>
            {actionLoading ? i18n.t("subscription.updating") : i18n.t("subscription.refreshing")}
          </Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

function SummaryRow({
  label,
  value,
  dark = false,
}: {
  label: string;
  value: string;
  dark?: boolean;
}) {
  return (
    <View style={styles.summaryRow}>
      <Text style={[styles.summaryLabel, dark && styles.summaryLabelDark]}>
        {label}
      </Text>
      <Text style={[styles.summaryValue, dark && styles.summaryValueDark]}>
        {value}
      </Text>
    </View>
  );
}

function StatusBadge({
  status,
  dark = false,
}: {
  status: string;
  dark?: boolean;
}) {
  const tone = statusColors(status);

  return (
    <View
      style={[
        styles.statusBadge,
        { backgroundColor: dark ? "#23374A" : tone.background },
      ]}
    >
      <View style={[styles.statusDot, { backgroundColor: tone.text }]} />
      <Text
        style={[
          styles.statusText,
          { color: dark ? "#F6F0E6" : tone.text },
        ]}
      >
        {i18n.t(`subscription.status.${status.toLowerCase()}`, { defaultValue: status.replace(/_/g, " ") })}
      </Text>
    </View>
  );
}

function PlanCard({
  plan,
  selected,
  current,
  expanded,
  interval,
  canSelect,
  disabled,
  onSelect,
  onToggleDetails,
}: {
  plan: Plan;
  selected: boolean;
  current: boolean;
  expanded: boolean;
  interval: BillingInterval;
  canSelect: boolean;
  disabled: boolean;
  onSelect: () => void;
  onToggleDetails: () => void;
}) {
  const price =
    interval === "YEARLY" ? plan.price_yearly : plan.price_monthly;
  const original =
    interval === "YEARLY"
      ? plan.price_yearly_original
      : plan.price_monthly_original;

  const hasOffer =
    original != null && Number(original) > Number(price);

  const features = Object.entries(plan.features ?? {}).filter(
    ([, value]) => value === true,
  );
  const quotas = Object.entries(plan.quotas ?? {});

  return (
    <View
      style={[
        styles.planCard,
        selected && styles.planCardSelected,
        current && styles.planCardCurrent,
      ]}
    >
      <Pressable
        onPress={onSelect}
        disabled={!canSelect || disabled}
        accessibilityRole="button"
        accessibilityState={{ selected, disabled: !canSelect || disabled }}
        style={styles.planSelectArea}
      >
        <View style={styles.planTopRow}>
          <View style={styles.planCopy}>
            <View style={styles.planNameRow}>
              <Text style={styles.planName}>{plan.name}</Text>
              {current ? <Text style={styles.currentTag}>{i18n.t("subscription.planCurrent")}</Text> : null}
            </View>
            {plan.description ? (
              <Text style={styles.planDescription}>{plan.description}</Text>
            ) : null}
          </View>
          <View style={[styles.radio, selected && styles.radioSelected]}>
            {selected ? <View style={styles.radioInner} /> : null}
          </View>
        </View>

        <View style={styles.priceRow}>
          <Text style={styles.price}>{formatMoney(price, plan.currency, i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK")}</Text>
          {hasOffer ? (
            <Text style={styles.originalPrice}>
              {formatMoney(original, plan.currency, i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK")}
            </Text>
          ) : null}
          {plan.offer_label ? (
            <Text style={styles.offerTag}>{plan.offer_label}</Text>
          ) : null}
        </View>

        <Text style={styles.priceCaption}>
          {interval === "YEARLY" ? i18n.t("subscription.planPerYear") : i18n.t("subscription.planPerMonth")}
          {plan.trial_days > 0 ? ` · ${plan.trial_days} ${i18n.t("subscription.dayTrial")}` : ""}
        </Text>
      </Pressable>

      <Pressable
        onPress={onToggleDetails}
        style={styles.detailsToggle}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
      >
        <Text style={styles.detailsToggleText}>
          {expanded ? i18n.t("subscription.hidePlanDetails") : i18n.t("subscription.viewPlanDetails")}
        </Text>
        <Text style={styles.chevron}>{expanded ? "⌃" : "›"}</Text>
      </Pressable>

      {expanded ? (
        <View style={styles.planDetails}>
          {plan.offer_ends_at ? (
            <SummaryRow label={i18n.t("subscription.offerEnds")} value={formatDate(plan.offer_ends_at, i18n.resolvedLanguage === "ur" ? "ur-PK" : "en-PK")} />
          ) : null}

          {features.length ? (
            <View style={styles.detailGroup}>
              <Text style={styles.detailGroupTitle}>{i18n.t("subscription.features")}</Text>
              {features.map(([feature]) => (
                <Text key={feature} style={styles.featureLine}>
                  ✓ {feature.replace(/_/g, " ")}
                </Text>
              ))}
            </View>
          ) : null}

          {quotas.length ? (
            <View style={styles.detailGroup}>
              <Text style={styles.detailGroupTitle}>{i18n.t("subscription.limits")}</Text>
              {quotas.map(([metric, limit]) => (
                <SummaryRow
                  key={metric}
                  label={metricLabel(metric)}
                  value={`${metricValue(metric, limit as number | null)}${
                    plan.limit_policy?.[metric]
                      ? ` · ${plan.limit_policy[metric]}`
                      : ""
                  }`}
                />
              ))}
            </View>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function UsageRow({ metric }: { metric: UsageMetric }) {
  const unlimited = metric.limit == null;
  const percentage =
    metric.percentage == null
      ? null
      : Math.max(0, Math.min(100, metric.percentage));

  const fillColor =
    percentage != null && percentage >= 100
      ? C.red
      : percentage != null && percentage >= 80
        ? C.amber
        : C.green;

  return (
    <View style={styles.usageRow}>
      <View style={styles.usageHeader}>
        <Text style={styles.usageName}>{metricLabel(metric.metric)}</Text>
        <Text style={styles.usageNumbers}>
          {metricValue(metric.metric, metric.used)}
          {" / "}
          {unlimited ? i18n.t("subscription.unlimited") : metricValue(metric.metric, metric.limit)}
        </Text>
      </View>

      {!unlimited && percentage != null ? (
        <>
          <View
            style={styles.progressTrack}
            accessibilityRole="progressbar"
            accessibilityValue={{ min: 0, max: 100, now: percentage }}
          >
            <View
              style={[
                styles.progressFill,
                { width: `${percentage}%`, backgroundColor: fillColor },
              ]}
            />
          </View>
          <Text style={styles.usageFootnote}>
            {metric.remaining != null
              ? `${metricValue(metric.metric, metric.remaining)} remaining`
              : `${percentage.toFixed(0)}% used`}
          </Text>
        </>
      ) : (
        <Text style={styles.usageFootnote}>
          {unlimited ? i18n.t("subscription.noSetLimit") : i18n.t("subscription.percentUsed", { percent: percentage ?? 0 })}
        </Text>
      )}
    </View>
  );
}

function PrimaryButton({
  label,
  onPress,
  loading = false,
  disabled = false,
  danger = false,
  style,
}: {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  danger?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.primaryButton,
        danger && styles.dangerButton,
        (disabled || loading) && styles.disabledButton,
        pressed && !disabled && !loading && styles.pressedButton,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color="#FFFFFF" />
      ) : (
        <Text style={styles.primaryButtonText}>{label}</Text>
      )}
    </Pressable>
  );
}

function SecondaryButton({
  label,
  onPress,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.secondaryButton,
        disabled && styles.disabledButton,
        pressed && !disabled && styles.pressedButton,
      ]}
    >
      <Text style={styles.secondaryButtonText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: C.background },
  content: { paddingHorizontal: 18, paddingTop: 21, paddingBottom: 40 },
  loadingScreen: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10, backgroundColor: C.background },
  pageHeader: { marginBottom: 21 },
  backLink: { alignSelf: "flex-start", paddingVertical: 7, paddingRight: 10, marginBottom: 10 },
  backText: { color: C.navy, fontSize: 13, fontWeight: "700" },
  pageTitle: { color: C.text, fontSize: 28, fontWeight: "800" },
  section: { marginBottom: 24 },
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: "800", marginBottom: 11 },
  sectionSubtitle: { color: C.secondary, fontSize: 11, marginTop: 4 },
  currentPlanCard: { backgroundColor: C.navy, borderRadius: 17, padding: 17 },
  currentPlanTop: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 10 },
  currentPlanCopy: { flex: 1 },
  currentPlanName: { color: "#FFFFFF", fontSize: 21, fontWeight: "800" },
  currentPlanSubline: { color: "#C0C9D3", fontSize: 12, marginTop: 5 },
  darkDivider: { height: 1, backgroundColor: "#334152", marginVertical: 13 },
  summaryRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: 12, paddingVertical: 7 },
  summaryLabel: { flex: 1, color: C.muted, fontSize: 11 },
  summaryValue: { flex: 1.4, color: C.text, fontSize: 11, fontWeight: "700", textAlign: "right" },
  summaryLabelDark: { color: "#B7C1CE" },
  summaryValueDark: { color: "#FFFFFF" },
  statusBadge: { flexDirection: "row", alignItems: "center", gap: 6, borderRadius: 99, paddingHorizontal: 9, paddingVertical: 6 },
  statusDot: { width: 7, height: 7, borderRadius: 4 },
  statusText: { fontSize: 10, fontWeight: "800" },
  darkNotice: { backgroundColor: "#263548", borderRadius: 10, padding: 10, marginTop: 9 },
  darkNoticeText: { color: "#F2DDAE", fontSize: 11, lineHeight: 16 },
  summaryAction: { marginTop: 10 },
  planCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 15, padding: 14, marginBottom: 9 },
  planCardSelected: { borderColor: C.navy, borderWidth: 2 },
  planCardCurrent: { backgroundColor: "#FBF8F1" },
  planSelectArea: { paddingBottom: 2 },
  planTopRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  planCopy: { flex: 1 },
  planNameRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 7 },
  planName: { color: C.text, fontSize: 16, fontWeight: "800" },
  currentTag: { color: C.green, backgroundColor: C.greenBg, borderRadius: 99, paddingHorizontal: 7, paddingVertical: 3, fontSize: 9, fontWeight: "800" },
  planDescription: { color: C.secondary, fontSize: 11, lineHeight: 16, marginTop: 4 },
  radio: { width: 20, height: 20, borderRadius: 10, borderWidth: 1.5, borderColor: "#BDB2A2", alignItems: "center", justifyContent: "center" },
  radioSelected: { borderColor: C.navy },
  radioInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.navy },
  priceRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8, marginTop: 13 },
  price: { color: C.navy, fontSize: 19, fontWeight: "800" },
  originalPrice: { color: C.muted, fontSize: 12, textDecorationLine: "line-through" },
  offerTag: { color: C.green, backgroundColor: C.greenBg, borderRadius: 99, paddingHorizontal: 8, paddingVertical: 4, fontSize: 10, fontWeight: "800" },
  priceCaption: { color: C.muted, fontSize: 10, marginTop: 2 },
  detailsToggle: { minHeight: 37, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderTopWidth: 1, borderTopColor: "#F0E9DC", marginTop: 12, paddingTop: 8 },
  detailsToggleText: { color: C.navy, fontSize: 11, fontWeight: "700" },
  chevron: { color: C.muted, fontSize: 21 },
  planDetails: { borderTopWidth: 1, borderTopColor: "#F0E9DC", marginTop: 4, paddingTop: 7 },
  detailGroup: { marginTop: 9 },
  detailGroupTitle: { color: C.secondary, fontSize: 10, fontWeight: "800", textTransform: "uppercase", letterSpacing: 0.7, marginBottom: 4 },
  featureLine: { color: C.secondary, fontSize: 11, paddingVertical: 3, textTransform: "capitalize" },
  actionCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 15, padding: 15, marginTop: 10 },
  actionCardTitle: { color: C.text, fontSize: 15, fontWeight: "800" },
  actionCardDescription: { color: C.secondary, fontSize: 11, lineHeight: 16, marginTop: 4 },
  fieldLabel: { color: C.secondary, fontSize: 11, fontWeight: "700", marginTop: 13, marginBottom: 6 },
  segment: { flexDirection: "row", gap: 8 },
  segmentButton: { flex: 1, minHeight: 42, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 8 },
  segmentButtonSelected: { backgroundColor: C.navy, borderColor: C.navy },
  segmentText: { color: C.secondary, fontSize: 12, fontWeight: "700" },
  segmentTextSelected: { color: "#FFFFFF" },
  input: { minHeight: 46, borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, color: C.text, fontSize: 14, paddingHorizontal: 12, paddingVertical: 10 },
  textArea: { minHeight: 76, textAlignVertical: "top" },
  primaryButton: { minHeight: 47, alignItems: "center", justifyContent: "center", borderRadius: 11, backgroundColor: C.navy, paddingHorizontal: 14, paddingVertical: 12, marginTop: 13 },
  dangerButton: { backgroundColor: C.red },
  primaryButtonText: { color: "#FFFFFF", fontSize: 12, fontWeight: "800", textAlign: "center" },
  secondaryButton: { minHeight: 43, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: C.border, borderRadius: 10, backgroundColor: C.surface, paddingHorizontal: 12, paddingVertical: 10, marginTop: 9 },
  secondaryButtonText: { color: C.navy, fontSize: 12, fontWeight: "800" },
  disabledButton: { opacity: 0.5 },
  pressedButton: { opacity: 0.75 },
  accordionHeader: { flexDirection: "row", alignItems: "center", backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 13 },
  accordionCopy: { flex: 1 },
  accordionIcon: { color: C.muted, fontSize: 23, marginLeft: 10 },
  usageCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 4, marginTop: 8 },
  usageRow: { paddingVertical: 11, borderBottomWidth: 1, borderBottomColor: "#F0E9DC" },
  usageHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  usageName: { color: C.text, fontSize: 12, fontWeight: "700" },
  usageNumbers: { color: C.secondary, fontSize: 11, textAlign: "right" },
  progressTrack: { height: 7, borderRadius: 5, backgroundColor: "#EEE8DD", overflow: "hidden", marginTop: 8 },
  progressFill: { height: "100%", borderRadius: 5 },
  usageFootnote: { color: C.muted, fontSize: 10, marginTop: 5 },
  infoCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 13, padding: 14 },
  infoTitle: { color: C.text, fontSize: 13, fontWeight: "800", marginBottom: 4 },
  muted: { color: C.secondary, fontSize: 12, lineHeight: 18 },
  errorCard: { backgroundColor: C.redBg, borderWidth: 1, borderColor: "#EAC6C0", borderRadius: 12, padding: 13, marginBottom: 14 },
  errorTitle: { color: C.red, fontSize: 13, fontWeight: "800" },
  errorText: {color: C.secondary, fontSize: 12, lineHeight: 18, marginTop: 4,},
  retryButton: {alignSelf: "flex-start", backgroundColor: C.surface, borderWidth: 1, borderColor: "#EAC6C0", borderRadius: 9, paddingHorizontal: 12, paddingVertical: 8, marginTop: 10,},
  retryText: { color: C.red, fontSize: 11, fontWeight: "800" },
  warningCard: {backgroundColor: C.amberBg, borderRadius: 10, padding: 10, marginTop: 10,},
  warningText: { color: C.amber, fontSize: 11, lineHeight: 16 },
  progressRow: {flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingTop: 14,},
  progressText: { color: C.muted, fontSize: 11 },
  topBar: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 10,},
  });
