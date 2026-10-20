import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, ErrorState, LoadingState } from "../../../../organizations/components/OrganizationUi";
import { useRateGaps } from "../hooks/useSchedules";
import { GAP_REASON_LABEL, gapTone } from "../utils/schedules.utils";

export function RateGapsPanel({ versionId }: { versionId: string }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const query = useRateGaps(versionId, open);
  const data = query.data;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">{t("schedules.gaps.title", "Missing rates")}</div>
        <Button variant="ghost" size="sm" onClick={() => setOpen((v) => !v)}>{open ? t("schedules.gaps.hide", "Hide") : t("schedules.gaps.show", "Why are lines unpriced?")}</Button>
      </div>
      {open ? (
        query.isLoading ? <LoadingState label={t("schedules.gaps.loading", "Checking the rate books…")} /> : query.isError || !data ? (
          <ErrorState title={t("schedules.gaps.error", "We couldn't check for missing rates")} onRetry={() => void query.refetch()} />
        ) : (
          <div className="space-y-3">
            {data.resolvable > 0 ? (
              <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-info-bg)] px-3 py-2 text-[12.5px] text-[var(--color-text-secondary)]">
                {t("schedules.gaps.resolvable", "{{n}} unpriced lines do have a rate in your books. Press “Price again” to apply it.", { n: data.resolvable })}
              </div>
            ) : null}
            {data.gaps.length === 0 ? (
              <div className="text-[12.5px] text-[var(--color-text-secondary)]">{t("schedules.gaps.none", "Every unpriced line has a rate available.")}</div>
            ) : (
              <ul className="divide-y divide-[var(--color-border)] rounded-[10px] border border-[var(--color-border)]">
                {data.gaps.map((g) => (
                  <li key={`${g.work_item_code}-${g.unit}-${g.reason}`} className="flex flex-wrap items-start justify-between gap-3 px-3 py-2.5 text-[12.5px]">
                    <div className="min-w-0">
                      <div><span className="font-mono font-semibold">{g.work_item_code ?? t("schedules.gaps.noCode", "(no code)")}</span> · {g.unit}</div>
                      <div className="max-w-[420px] truncate text-[var(--color-text-muted)]">{g.sample_description ?? "—"}</div>
                      {g.reason === "UNIT_MISMATCH" && g.available_units.length > 0 ? (
                        <div className="text-[var(--color-text-secondary)]">{t("schedules.gaps.haveUnits", "A rate exists per {{units}}, which can't be converted to {{unit}}.", { units: g.available_units.join(", "), unit: g.unit })}</div>
                      ) : null}
                    </div>
                    <div className="text-right">
                      <Badge tone={gapTone(g.reason)}>{t(`schedules.gaps.reason.${g.reason}`, GAP_REASON_LABEL[g.reason])}</Badge>
                      <div className="mt-1 text-[var(--color-text-muted)]">{t("schedules.gaps.lines", "{{n}} lines · quantity {{q}}", { n: g.lines, q: g.quantity })}</div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )
      ) : null}
    </div>
  );
}
