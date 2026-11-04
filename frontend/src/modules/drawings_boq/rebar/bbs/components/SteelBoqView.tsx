import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../../organizations/components/OrganizationUi";
import { STATE_WORDS, actionWords, canPress, itemSentence, whyNothing } from "../utils/steelBoq";
import type { SteelBoq } from "../types/steelBoq.types";

interface Props {
  data: SteelBoq;
  canAdjust: boolean;
  applying?: boolean;
  onApply?: () => void;
}

export function SteelBoqView({ data, canAdjust, applying, onApply }: Props) {
  const { t } = useTranslation();
  const action = actionWords(data);
  const why = whyNothing(data);
  return (
    <div className="space-y-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3" data-testid="steel-boq">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("steelBoq.title", "Steel on the bill")}</span>
        <Badge tone={data.in_sync ? "green" : "gold"}>{t(`steelBoq.state.${data.state}`, STATE_WORDS[data.state])}</Badge>
      </div>
      <p className="text-[12.5px] text-[var(--color-text-primary)]" data-testid="steel-boq-item">{itemSentence(data)}</p>
      {why ? <p className="text-[12px] text-[var(--color-text-secondary)]" data-testid="steel-boq-why">{why}</p> : null}
      {data.open_count > 0 && data.source === "BBS_AUDITED" ? (
        <p className="text-[12px] text-[var(--color-text-secondary)]">{t("steelBoq.open", "{{n}} finding(s) are still open and are not on the bill.", { n: data.open_count })}</p>
      ) : null}
      {canPress(data, canAdjust) && onApply && action ? (
        <Button variant="primary" size="sm" disabled={applying} onClick={onApply} data-testid="steel-boq-apply">
          {t(`steelBoq.action.${data.state}`, action)}
        </Button>
      ) : null}
      {action && !canAdjust ? <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("steelBoq.noRight", "You need the right to adjust BOQ quantities to change this.")}</p> : null}
    </div>
  );
}
