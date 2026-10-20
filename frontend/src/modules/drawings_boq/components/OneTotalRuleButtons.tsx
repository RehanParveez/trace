import { useTranslation } from "react-i18next";
import type { OneTotalPrefer, OneTotalRuleKind } from "../api/oneTotal.api";
import { useOneTotalRules, useRemoveOneTotalRule, useSetOneTotalRule } from "../hooks/useOneTotal";
import { PREFER_HELP, PREFER_LABEL, PREFER_ORDER, ruleFor } from "../utils/oneTotalRules";

interface Props {
  projectId: string | undefined;
  kind: OneTotalRuleKind;
  mark: string | null | undefined;
  levelName?: string | null;
  used?: OneTotalPrefer | null;
}

const BTN = "rounded-[6px] border px-2 py-0.5 text-[10.5px] font-semibold disabled:opacity-50";
const ON = "border-[var(--color-trace-gold-dark)] bg-[var(--color-warning-bg)] text-[var(--color-text-primary)]";
const OFF = "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]";

export function OneTotalRuleButtons({ projectId, kind, mark, levelName, used }: Props) {
  const { t } = useTranslation();
  const rules = useOneTotalRules(projectId);
  const set = useSetOneTotalRule(projectId);
  const remove = useRemoveOneTotalRule(projectId);
  if (!projectId || (kind === "ITEM" && !mark)) return null;
  const current = ruleFor(rules.data, kind, mark, levelName);
  const busy = set.isPending || remove.isPending;
  return (
    <div className="mt-1 flex flex-wrap items-center gap-1" data-testid={`rule-buttons-${kind}-${mark ?? ""}`}>
      {PREFER_ORDER.map((p) => (
        <button
          key={p}
          type="button"
          disabled={busy}
          aria-pressed={current?.prefer === p}
          title={t(`boq.oneTotal.rule.help.${p}`, PREFER_HELP[p])}
          className={`${BTN} ${current?.prefer === p ? ON : OFF}`}
          onClick={() => set.mutate({ kind, mark: mark ?? "", level_name: levelName ?? "", prefer: p })}
        >
          {t(`boq.oneTotal.rule.${p}`, PREFER_LABEL[p])}
        </button>
      ))}
      {current ? (
        <button type="button" disabled={busy} className={`${BTN} ${OFF}`} onClick={() => remove.mutate(current.id)}>
          {t("boq.oneTotal.rule.clear", "Clear")}
        </button>
      ) : null}
      {current && current.prefer !== used ? (
        <span className="text-[10.5px] text-[var(--color-warning)]">{t("boq.oneTotal.rule.nextRun", "Applies from the next run.")}</span>
      ) : null}
      {set.isError || remove.isError ? <span className="text-[10.5px] text-[var(--color-danger)]">{t("boq.oneTotal.rule.failed", "Could not save the choice. Try again.")}</span> : null}
    </div>
  );
}
