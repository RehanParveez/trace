import { useTranslation } from "react-i18next";
import { useOneTotalRules, useRemoveOneTotalRule } from "../hooks/useOneTotal";
import { PREFER_LABEL, scopeWords } from "../utils/oneTotalRules";

export function OneTotalRulesList({ projectId }: { projectId: string | undefined }) {
  const { t } = useTranslation();
  const rules = useOneTotalRules(projectId);
  const remove = useRemoveOneTotalRule(projectId);
  const list = rules.data ?? [];
  if (!projectId || list.length === 0) return null;
  return (
    <div className="space-y-1" data-testid="one-total-rules">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.oneTotal.rules.title", "Your choices for this project")}</div>
      <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
        {list.map((r) => (
          <li key={r.id} className="flex flex-wrap items-baseline gap-2" data-testid={`one-total-rule-${r.id}`}>
            <span className="font-mono font-semibold text-[var(--color-text-primary)]">{scopeWords(r)}</span>
            <span>{t(`boq.oneTotal.rule.${r.prefer}`, PREFER_LABEL[r.prefer])}</span>
            <button type="button" disabled={remove.isPending} className="text-[11px] font-semibold text-[var(--color-trace-gold-dark)] underline" onClick={() => remove.mutate(r.id)}>
              {t("boq.oneTotal.rule.clear", "Clear")}
            </button>
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-[var(--color-text-muted)]">{t("boq.oneTotal.rules.note", "A choice for a mark beats one for the kind, and one for a storey beats one for every storey. They apply from the next run.")}</p>
    </div>
  );
}
