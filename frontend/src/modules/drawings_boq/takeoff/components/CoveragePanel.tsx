import { useTranslation } from "react-i18next";
import type { RegisterSyncResult } from "../types/takeoff.types";
import { mixSlices, rangedTotals, sharePct, totalCaveat, totalLine } from "../utils/coverage";
import { EVIDENCE_LABEL, type EvidenceGrade } from "../utils/evidence";

const BAR: Record<EvidenceGrade, string> = {
  PRINTED: "bg-[var(--color-success)]",
  MEASURED: "bg-[var(--color-info,#3b82f6)]",
  ASSUMED: "bg-[var(--color-warning)]",
  MISSING: "bg-[var(--color-danger)]",
};

export function CoveragePanel({ register }: { register: Pick<RegisterSyncResult, "totals" | "source_mix"> | undefined }) {
  const { t } = useTranslation();
  const totals = rangedTotals(register?.totals);
  const mix = register?.source_mix ?? {};
  const units = Object.keys(mix).filter((u) => u && mixSlices(mix[u]).length > 0).sort();
  if (!register || (units.length === 0 && totals.length === 0)) return null;
  return (
    <section className="space-y-2" data-testid="coverage-panel">
      <h4 className="font-semibold text-[var(--color-text-primary)]">{t("drawings.coverage.title", "How the quantities are known")}</h4>
      {units.map((unit) => (
        <div key={unit} data-testid={`coverage-mix-${unit}`}>
          <div className="flex h-2 overflow-hidden rounded-full bg-[var(--color-border)]" role="img" aria-label={unit}>
            {mixSlices(mix[unit]).map((s) => <div key={s.grade} className={BAR[s.grade]} style={{ width: `${s.share * 100}%` }} />)}
          </div>
          <p className="mt-0.5 text-[11px] text-[var(--color-text-secondary)]">
            {unit}: {mixSlices(mix[unit]).map((s) => `${sharePct(s.share)} ${t(`drawings.elements.evidence.${s.grade}`, EVIDENCE_LABEL[s.grade]).toLowerCase()}`).join(", ")}
          </p>
        </div>
      ))}
      {totals.length > 0 ? (
        <ul className="list-none space-y-1 pl-0" data-testid="coverage-ranges">
          {totals.map((r) => (
            <li key={r.unit} className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid={`coverage-range-${r.unit}`}>
              <span className="font-mono">{totalLine(r)}</span>
              {totalCaveat(r) ? <span className="block text-[var(--color-text-muted)]">{totalCaveat(r)}.</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
