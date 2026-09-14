import { StatCard } from "../../organizations/components/OrganizationUi";
import { useAIUsageSummary } from "../hooks";
import { formatLatency } from "../utils/ai-requests.utils";
import { useTranslation } from "react-i18next";

export function AIUsageSummaryCards() {
  const summaryQuery = useAIUsageSummary();
  const { t } = useTranslation();
  const summary = summaryQuery.data;

  const successRate = summary && summary.total_requests > 0
    ? Math.round((summary.succeeded / summary.total_requests) * 100)
    : null;

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label={t("ai.summary.total")} value={summary?.total_requests ?? 0} note={t("ai.summary.totalNote")} icon="settings" tone="blue" />
      <StatCard label={t("ai.summary.succeeded")} value={summary?.succeeded ?? 0} note={successRate !== null ? t("ai.summary.successRate", { rate: successRate }) : "—"} icon="check" tone="green" />
      <StatCard label={t("ai.summary.failed")} value={summary?.failed ?? 0} note={t("ai.summary.avgLatencyNote")} icon="alert" tone="red" />
      <StatCard label={t("ai.summary.avgLatency")} value={formatLatency(summary?.average_latency_ms ?? null)} note={t("ai.summary.avgLatencyNote")} icon="clock" tone="gold" />
    </div>
  );
}