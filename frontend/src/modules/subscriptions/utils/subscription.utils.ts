import type {BillingInterval, SubscriptionStatus,
} from "../types/subscription.types";
import i18n from "../../../i18n";

export function formatSubscriptionStatus(
  status: SubscriptionStatus,
): string {
  switch (status) {
    case "TRIALING":
      return i18n.t("subscription.status.trialing");
    case "ACTIVE":
      return i18n.t("subscription.status.active");
    case "PAST_DUE":
      return i18n.t("subscription.status.pastDue");
    case "CANCELLED":
      return i18n.t("subscription.status.cancelled");
    case "EXPIRED":
      return i18n.t("subscription.status.expired");
    default:
      return status;
  }
}

export function getSubscriptionStatusTone(
  status: SubscriptionStatus,
): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "ACTIVE":
    case "TRIALING":
      return "green";

    case "PAST_DUE":
      return "gold";

    case "CANCELLED":
    case "EXPIRED":
      return "red";

    default:
      return "slate";
  }
}

export function formatBillingInterval(
  interval: BillingInterval,
): string {
  return interval === "YEARLY"
    ? i18n.t("subscription.interval.yearly")
    : i18n.t("subscription.interval.monthly");
}

export function formatPrice(
  price: number | string,
  currency: string,
): string {
  const numericPrice =
    typeof price === "string" ? Number(price) : price;

  if (!Number.isFinite(numericPrice) || numericPrice === 0) {
    return i18n.t("subscription.free");
  }
  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(numericPrice);
}

export function formatDate(
  value: string | null,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatBytes(
  bytes: number,
): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 ** 2) {
    return `${Math.round(bytes / 1024)} KB`;
  }

  if (bytes < 1024 ** 3) {
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  }

  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}

export function formatQuota(
  metric: string,
  value: number | null,
): string {
  if (value === null) {
    return i18n.t("subscription.unlimited");
  }

  if (metric === "storage_bytes") {
    return formatBytes(value);
  }

  return value.toLocaleString("en-PK");
}

export function formatMetricLabel(
  metric: string,
): string {
  switch (metric) {
    case "projects":
      return i18n.t("subscription.metric.projects");
    case "storage_bytes":
      return i18n.t("subscription.metric.storage");
    case "site_photos":
      return i18n.t("subscription.metric.sitePhotos");
    case "drawings":
      return i18n.t("subscription.metric.drawings");
    case "ai_requests":
      return i18n.t("subscription.metric.aiRequests");
    default:
      return metric
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) =>
          letter.toUpperCase(),
      );
  }
}

export function createIdempotencyKey(): string {
  return crypto.randomUUID();
}