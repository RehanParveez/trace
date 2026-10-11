import { useLabourDaySummary } from "../../labour/hooks";
import { useTranslation } from "react-i18next";

export function LabourDayCrossCheck({ projectId, date, reported }: { projectId: string; date: string; reported?: number | null }) {
  const { t } = useTranslation();
  const summaryQuery = useLabourDaySummary(projectId, date);
  const total = summaryQuery.data?.total_present;

  if (!summaryQuery.data || Number(total) === 0) return null;

  const mismatch = reported !== null && reported !== undefined && Math.abs(Number(total) - reported) > 0.5;
  const tradeText = summaryQuery.data.by_trade.length > 0
    ? ` (${summaryQuery.data.by_trade.map((row) => `${row.cost} ${row.trade}`).join(", ")})`
    : "";

  return (
    <div className={`mt-2 rounded-[8px] border px-3 py-2 text-[12px] ${mismatch ? "border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] text-[var(--color-danger)]" : "border-[var(--color-info)]/25 bg-[var(--color-info-bg)] text-[var(--color-info)]"}`}>
      {t("siteProgress.crossCheck.recordsShow", { total })}{tradeText}.
      {mismatch ? <> {t("siteProgress.crossCheck.mismatch", { reported })}</> : null}
    </div>
  );
}