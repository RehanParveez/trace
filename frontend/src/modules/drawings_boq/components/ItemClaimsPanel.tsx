import { useTranslation } from "react-i18next";
import type { PdfTakeoffStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { itemClaims, ruleWords } from "../utils/oneTotalRules";
import { OneTotalRuleButtons } from "./OneTotalRuleButtons";

const TITLE = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const TH = "px-2 py-1.5 text-left text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const TD = "px-2 py-1.5 font-mono text-[12px] text-[var(--color-text-primary)]";

export function ItemClaimsPanel({ takeoff, projectId }: { takeoff: PdfTakeoffStats | null | undefined; projectId?: string }) {
  const { t } = useTranslation();
  const claims = itemClaims(takeoff?.variances);
  if (claims.length === 0) return null;
  return (
    <div className="space-y-1.5" data-testid="item-claims">
      <div className={TITLE}>{t("boq.itemClaims.title", "Work items measured by both the model and the drawings")}</div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            <tr className="border-b border-[var(--color-border)]">
              <th className={TH}>{t("boq.itemClaims.item", "Work item")}</th>
              <th className={TH}>{t("boq.itemClaims.drawing", "Drawings")}</th>
              <th className={TH}>{t("boq.itemClaims.model", "Model")}</th>
              <th className={TH}>{t("boq.itemClaims.difference", "Difference")}</th>
              <th className={TH}>{t("boq.itemClaims.counts", "Which counts")}</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((c) => (
              <tr key={`${c.code}-${c.levelName ?? ""}-${c.unit}`} className="border-b border-[var(--color-border)] align-top" data-testid={`item-claim-${c.code}`}>
                <td className={TD}>
                  {c.code}
                  {c.levelName ? <span className="block text-[10px] text-[var(--color-text-muted)]">{c.levelName}</span> : null}
                </td>
                <td className={TD}>{formatPrecise(c.drawing, 3)} {c.unit}</td>
                <td className={TD}>{formatPrecise(c.model, 3)} {c.unit}</td>
                <td className={`${TD} ${c.over ? "text-[var(--color-warning)]" : ""}`}>{Number(c.variancePct) > 0 ? "+" : ""}{c.variancePct}%</td>
                <td className="px-2 py-1.5 text-[12px] text-[var(--color-text-secondary)]">
                  {c.rule ? ruleWords(c.rule) : t("boq.itemClaims.default", "the model (the drawing is only checked against it)")}
                  <OneTotalRuleButtons projectId={projectId} kind="ITEM" mark={c.code} levelName={c.levelName} used={c.rule} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
