import type {BillingInterval, SubscriptionStatus,
} from "../types/subscription.types";

export function formatSubscriptionStatus(
  status: SubscriptionStatus,
): string {
  switch (status) {
    case "TRIALING":
      return "Trialing";

    case "ACTIVE":
      return "Active";

    case "PAST_DUE":
      return "Past due";

    case "CANCELLED":
      return "Cancelled";

    case "EXPIRED":
      return "Expired";

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
  return interval === "YEARLY" ? "Yearly" : "Monthly";
}

export function formatPrice(
  price: number,
  currency: string,
): string {
  if (price === 0) {
    return "Free";
  }

  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(price);
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
    return "Unlimited";
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
      return "Projects";

    case "storage_bytes":
      return "Storage";

    case "site_photos":
      return "Site photos";

    case "drawings":
      return "Drawings";

    case "ai_requests":
      return "AI requests";

    default:
      return metric
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) =>
          letter.toUpperCase(),
        );
  }
}