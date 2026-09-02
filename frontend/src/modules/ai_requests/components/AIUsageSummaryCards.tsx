import { StatCard } from "../../organizations/components/OrganizationUi";
import { useAIUsageSummary } from "../hooks";
import { formatLatency } from "../utils/ai-requests.utils";

export function AIUsageSummaryCards() {
  const summaryQuery = useAIUsageSummary();
  const summary = summaryQuery.data;

  const successRate = summary && summary.total_requests > 0
    ? Math.round((summary.succeeded / summary.total_requests) * 100)
    : null;

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Total requests" value={summary?.total_requests ?? 0} note="This billing period" icon="settings" tone="blue" />
      <StatCard label="Succeeded" value={summary?.succeeded ?? 0} note={successRate !== null ? `${successRate}% success rate` : "—"} icon="check" tone="green" />
      <StatCard label="Failed" value={summary?.failed ?? 0} note="Errored or malformed output" icon="alert" tone="red" />
      <StatCard label="Avg latency" value={formatLatency(summary?.average_latency_ms ?? null)} note="Per request" icon="clock" tone="gold" />
    </div>
  );
}