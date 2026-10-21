import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DerivedStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { ringZoneSkipWords, ringZoneView, steelAllowanceSkipWords, steelAllowancesReasonWords, steelAllowancesView } from "../utils/steelAllowances";

const TITLE = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const NOTE = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]";
const WARN = "rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]";

function Cell({ label, value, testId }: { label: string; value: ReactNode; testId: string }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3" data-testid={testId}>
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{label}</div>
      <div className="mt-1.5 font-mono text-[15px] font-semibold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

export function SteelAllowancesPanel({ derived }: { derived: DerivedStats | null | undefined }) {
  const { t } = useTranslation();
  const allow = steelAllowancesView(derived);
  const rings = ringZoneView(derived);
  if (!allow && !rings) return null;
  return (
    <div className="space-y-3" data-testid="steel-allowances">
      {allow ? (
        allow.ran ? (
          <div className="space-y-2" data-testid="steel-allowances-ran">
            <div className={TITLE}>{t("boq.steelAllowances.title", "Binding wire and chairs")}</div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Cell testId="steel-allowances-bars" label={t("boq.steelAllowances.bars", "Reinforcement (kg)")} value={formatPrecise(allow.reinforcementKg, 1)} />
              {allow.wireKg !== null ? <Cell testId="steel-allowances-wire" label={t("boq.steelAllowances.wire", "Binding wire (kg)")} value={formatPrecise(allow.wireKg, 1)} /> : null}
              {allow.chairsKg !== null ? <Cell testId="steel-allowances-chairs" label={t("boq.steelAllowances.chairs", "Chairs (kg)")} value={formatPrecise(allow.chairsKg, 1)} /> : null}
              <Cell testId="steel-allowances-share" label={t("boq.steelAllowances.share", "Added to the bars (%)")} value={formatPrecise(allow.sharePct, 2)} />
            </div>
            <div className={NOTE} data-testid="steel-allowances-basis">
              {allow.wirePct !== null
                ? t("boq.steelAllowances.basisWire", { defaultValue: "Binding wire is {{pct}} % of the weight of the reinforcement of each storey. ", pct: allow.wirePct })
                : ""}
              {allow.chairsKgPerM2 !== null
                ? t("boq.steelAllowances.basisChairs", {
                    defaultValue: "Chairs are {{rate}} kg for each square metre of slab ({{area}} m² here). ",
                    rate: allow.chairsKgPerM2,
                    area: formatPrecise(allow.slabAreaM2, 1),
                  })
                : ""}
              {t("boq.steelAllowances.basisNone", "Neither is drawn, so every row is marked assumed. The weight of the bars is not changed.")}
            </div>
            {allow.wireAssumed || allow.chairsAssumed ? (
              <div className={WARN} data-testid="steel-allowances-assumed">
                {t("boq.steelAllowances.assumed", "The standard value is used for the percentage or the rate. Set it in the run settings once the site's practice is known.")}
              </div>
            ) : null}
            {allow.skipped.length > 0 ? (
              <div className={NOTE} data-testid="steel-allowances-skipped">
                {t("boq.steelAllowances.skipped", "Left out:")} {allow.skipped.map((s) => `${s.count} (${steelAllowanceSkipWords(s.code)})`).join("; ")}
              </div>
            ) : null}
          </div>
        ) : (
          <div className={NOTE} data-testid="steel-allowances-not-run">
            {t("boq.steelAllowances.notRun", "Binding wire and chairs were not worked out.")} {steelAllowancesReasonWords(allow.reason)}
          </div>
        )
      ) : null}
      {rings ? (
        <div className="space-y-2" data-testid="steel-ring-zone">
          <div className={TITLE}>{t("boq.steelAllowances.ringTitle", "Rings at the joints")}</div>
          <div className={NOTE}>
            {rings.marks > 0
              ? t("boq.steelAllowances.ringApplied", {
                  defaultValue:
                    "{{count}} column and beam member(s) had no closer ring zone printed, so one was given at each end: {{mm}} mm spacing over the longest of a sixth of the column height, the larger side and 450 mm (columns), or twice the depth (beams). Their rows are marked assumed.",
                  count: rings.marks,
                  mm: rings.denseSpacingMm ?? "",
                })
              : t("boq.steelAllowances.ringNone", "No member needed a closer ring zone.")}
            {rings.skipped.length > 0 ? ` ${t("boq.steelAllowances.ringLeft", "Left as they are:")} ${rings.skipped.map((s) => `${s.count} (${ringZoneSkipWords(s.code)})`).join("; ")}.` : ""}
          </div>
        </div>
      ) : null}
    </div>
  );
}
