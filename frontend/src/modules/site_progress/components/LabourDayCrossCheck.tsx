import { useLabourDaySummary } from "../../labour/hooks";

export function LabourDayCrossCheck({ projectId, date }: { projectId: string; date: string }) {
  const summaryQuery = useLabourDaySummary(projectId, date);
  const total = summaryQuery.data?.total_present;

  if (!summaryQuery.data || Number(total) === 0) return null;

  return (
    <div className="mt-2 rounded-[8px] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-3 py-2 text-[12px] text-[var(--color-info)]">
      Labour records show <strong>{total}</strong> present on this date
      {summaryQuery.data.by_trade.length > 0
        ? ` (${summaryQuery.data.by_trade.map((t) => `${t.cost} ${t.trade}`).join(", ")})`
        : ""}.
    </div>
  );
}