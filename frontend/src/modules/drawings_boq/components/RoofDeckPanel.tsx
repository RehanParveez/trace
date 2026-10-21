import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DerivedStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { roofDeckReasonWords, roofDeckView } from "../utils/roofDeck";

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

export function RoofDeckPanel({ derived }: { derived: DerivedStats | null | undefined }) {
  const { t } = useTranslation();
  const view = roofDeckView(derived);
  if (!view) return null;
  if (!view.ran) {
    return (
      <div className={NOTE} data-testid="roof-deck-not-run">
        {t("boq.roofDeck.notRun", "The layers of the roof deck were not worked out.")} {roofDeckReasonWords(view.reason)}
      </div>
    );
  }
  return (
    <div className="space-y-2" data-testid="roof-deck">
      <div className={TITLE}>{t("boq.roofDeck.title", "Roof deck layers")}</div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Cell testId="roof-deck-area" label={t("boq.roofDeck.area", "Roof area (m²)")} value={formatPrecise(view.roofAreaM2, 3)} />
        {view.membraneM2 !== null ? <Cell testId="roof-deck-membrane" label={t("boq.roofDeck.membrane", "Membrane (m²)")} value={formatPrecise(view.membraneM2, 3)} /> : null}
        {view.cobaM3 !== null ? <Cell testId="roof-deck-coba" label={t("boq.roofDeck.coba", "Coba (m³)")} value={formatPrecise(view.cobaM3, 3)} /> : null}
        {view.screedM2 !== null ? <Cell testId="roof-deck-screed" label={t("boq.roofDeck.screed", "Screed (m²)")} value={formatPrecise(view.screedM2, 3)} /> : null}
      </div>
      <div className={NOTE} data-testid="roof-deck-basis">
        {view.cobaThicknessMm !== null
          ? t("boq.roofDeck.basisCoba", {
              defaultValue:
                "Laid over {{count}} roof area row(s). The coba is the roof area times an average thickness of {{mm}} mm. None of the layers is printed on the drawings, so every row is marked assumed.",
              count: view.roofs,
              mm: view.cobaThicknessMm,
            })
          : t("boq.roofDeck.basis", {
              defaultValue: "Laid over {{count}} roof area row(s). None of the layers is printed on the drawings, so every row is marked assumed.",
              count: view.roofs,
            })}
      </div>
      {view.thicknessAssumed ? (
        <div className={WARN} data-testid="roof-deck-thickness-assumed">
          {t("boq.roofDeck.thicknessAssumed", "The thickness of the coba is the standard value. Set it in the run settings once the roof section is known.")}
        </div>
      ) : null}
      {view.skipped.length > 0 ? (
        <div className={NOTE}>
          {t("boq.modelWorks.skipped", "Left as they are:")} {view.skipped.join(", ")}
        </div>
      ) : null}
    </div>
  );
}
