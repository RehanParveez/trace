import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import { useQsProposed } from "../hooks/useProposed";
import { BASIS_LABEL, EFFECT_LABEL, EFFECT_ORDER, groupProposals, proposalCounts } from "../utils/qsProposed";
import type { ProposalEffect } from "../utils/qsProposed";

const TONE: Record<ProposalEffect, "gold" | "blue" | "slate" | "red"> = { VALUE: "gold", SUGGESTION: "blue", KEPT: "slate", HOLD: "red" };

export function ProposedAnswersPanel() {
  const { t } = useTranslation();
  const { data } = useQsProposed();
  if (!data || data.items.length === 0) return null;
  const counts = proposalCounts(data);
  const groups = groupProposals(data);
  return (
    <details className="mt-3 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3" data-testid="qs-proposed">
      <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-text-primary)]">
        {t("boq.proposed.title", "Proposed answers for the questions the QS did not answer")}
      </summary>
      <p className="mt-2 text-[11px] leading-snug text-[var(--color-text-muted)]">
        {t(
          "boq.proposed.hint",
          "These are not the QS's answers. They are proposed from the way he answered the other questions and from his workbook. A proposed number is used as the standard value and stays marked as assumed; type a value to override it. Nothing here is final until the QS confirms it.",
        )}
      </p>
      <div className="mt-2 flex flex-wrap gap-2" data-testid="qs-proposed-counts">
        {EFFECT_ORDER.map((effect) => (
          <Badge key={effect} tone={TONE[effect]}>
            {t(`boq.proposed.effect.${effect}`, EFFECT_LABEL[effect])}: {counts[effect]}
          </Badge>
        ))}
      </div>
      <div className="mt-3 space-y-3">
        {groups.map((group) => (
          <section key={group.section} data-testid={`qs-proposed-section-${group.section}`}>
            <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
              {group.section}. {t(`boq.proposed.section.${group.section}`, group.title)}
            </div>
            <ul className="mt-1.5 space-y-2">
              {group.items.map((item) => (
                <li key={item.id} className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2" data-testid={`qs-proposed-${item.id}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] font-semibold text-[var(--color-text-primary)]">{item.id}</span>
                    <span className="text-[12px] font-semibold text-[var(--color-text-primary)]">{item.topic}</span>
                    <Badge tone={TONE[item.effect]}>{t(`boq.proposed.effect.${item.effect}`, EFFECT_LABEL[item.effect])}</Badge>
                  </div>
                  <p className="mt-1 text-[12px] text-[var(--color-text-secondary)]">{item.proposed}</p>
                  <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                    {t(`boq.proposed.basis.${item.basis}`, BASIS_LABEL[item.basis])}. {item.evidence}
                  </p>
                  {item.confirm ? (
                    <p className="mt-1 text-[11px] font-semibold text-[var(--color-text-secondary)]">
                      {t("boq.proposed.confirm", "To confirm")}: {item.confirm}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </details>
  );
}
