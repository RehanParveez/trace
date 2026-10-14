import { useTranslation } from "react-i18next";
import type { DrawingFacts } from "../types/takeoff.types";
import { FACT_TITLE, conflictValueText, factDetail, floorToFloor, groupFacts, mmText, mmToFeetInches, pagesText } from "../utils/facts";

interface Props {
  facts: DrawingFacts | undefined;
  loading: boolean;
  failed: boolean;
}

export function DrawingFactsList({ facts, loading, failed }: Props) {
  const { t } = useTranslation();
  const groups = groupFacts(facts);
  const ftf = floorToFloor(facts);
  const conflicts = facts?.conflicts ?? [];
  if (!loading && !failed && groups.length === 0 && ftf === null) return null;
  return (
    <details className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-2.5" data-testid="drawing-facts">
      <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-text-primary)]">
        {t("drawings.facts.title", "What the drawings say")}
        {conflicts.length > 0 ? <span className="ml-2 text-[var(--color-danger)]">{t("drawings.facts.conflictCount", { defaultValue: "{{n}} to settle", n: conflicts.length })}</span> : null}
      </summary>
      <div className="mt-2 space-y-2">
        <p className="text-[11px] leading-snug text-[var(--color-text-muted)]">
          {t("drawings.facts.intro", "Read from the notes and level marks printed on the sheets. Trace does not apply them by itself; use them when you measure and check the quantities.")}
        </p>
        {loading ? <p className="text-[11px] text-[var(--color-text-muted)]">{t("drawings.facts.loading", "Reading the notes…")}</p> : null}
        {failed ? <p className="text-[11px] text-[var(--color-danger)]">{t("drawings.facts.failed", "The notes could not be listed just now.")}</p> : null}
        {conflicts.map((c) => (
          <div key={c.kind} className="rounded-[6px] bg-[var(--color-danger-bg)] p-2 text-[11.5px] text-[var(--color-danger)]" data-testid={`fact-conflict-${c.kind}`}>
            <div className="font-semibold">
              {t("drawings.facts.conflict", { defaultValue: "The drawings state the {{name}} two ways. Decide which is right before you measure.", name: t(`drawings.facts.kind.${c.kind}`, FACT_TITLE[c.kind]).toLowerCase() })}
            </div>
            <ul className="mt-1 list-none space-y-0.5 pl-0">
              {c.values.map((v) => (
                <li key={`${v.value_mm ?? v.value}`}>
                  {conflictValueText(v)} · {t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText(v.pages) })}
                  {v.scopes.length > 0 ? ` · ${v.scopes.join(", ")}` : ""}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {ftf !== null ? (
          <div className="text-[11.5px] text-[var(--color-text-primary)]" data-testid="fact-floor-to-floor">
            <span className="font-semibold">{t("drawings.facts.floorToFloor", "Floor to floor")}</span>{" "}
            {mmToFeetInches(ftf)} ({mmText(ftf)}){" "}
            <span className="text-[var(--color-text-muted)]">{t("drawings.facts.floorToFloorHint", "from the level marks on the elevations. The clear wall height is less by the slab and beam depth.")}</span>
          </div>
        ) : null}
        {groups.map((g) => (
          <div key={g.kind} className="text-[11.5px]">
            <div className="font-semibold text-[var(--color-text-primary)]">{t(`drawings.facts.kind.${g.kind}`, FACT_TITLE[g.kind])}</div>
            <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
              {g.facts.map((f) => (
                <li key={`${g.kind}-${f.scope}-${f.value_mm}-${f.value}-${f.grade}-${f.concrete_class}-${f.mix}-${f.where}`}>
                  {factDetail(f)} · {t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText(f.pages) })}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </details>
  );
}
