import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { BOQItemSpec } from "../types/drawings-boq.types";
import { derivedBasisRows, derivedHasAssumption, isDerivedSpec } from "../utils/derived";

function useBasisText(): (basis: "user" | "convention" | "default" | null) => string {
  const { t } = useTranslation();
  return (basis) => {
    if (basis === "user") return t("boq.derived.basis.user", "given");
    if (basis === "convention") return t("boq.derived.basis.convention", "set on the convention");
    if (basis === "default") return t("boq.derived.basis.default", "assumed");
    return "";
  };
}

export function DerivedBadge({ spec }: { spec?: BOQItemSpec | null }) {
  const { t } = useTranslation();
  const basisText = useBasisText();
  if (!isDerivedSpec(spec)) return null;
  const rows = derivedBasisRows(spec);
  const hint = [
    t("boq.derived.badgeHint", "Not drawn in the model. Worked out from the foundations."),
    ...rows.map((r) => `${t(`boq.derived.param.${r.key}`, r.key)}: ${r.value} (${basisText(r.basis)})`),
  ].join("\n");
  const assumed = derivedHasAssumption(spec);
  return (
    <span title={hint}>
      <Badge tone={assumed ? "gold" : "blue"}>
        {assumed ? t("boq.derived.badgeAssumed", "Derived · assumed") : t("boq.derived.badge", "Derived")}
      </Badge>
    </span>
  );
}

export function DerivedBasisList({ spec }: { spec?: BOQItemSpec | null }) {
  const { t } = useTranslation();
  const basisText = useBasisText();
  const rows = derivedBasisRows(spec);
  if (rows.length === 0) return null;
  return (
    <div className="space-y-1 rounded-[8px] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {t("boq.derived.basisTitle", "Assumptions used")}
      </div>
      <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
        {rows.map((r) => (
          <li key={r.key} className="flex flex-wrap items-baseline gap-2">
            <span>{t(`boq.derived.param.${r.key}`, r.key)}</span>
            <span className="font-mono font-semibold text-[var(--color-text-primary)]">{r.value}</span>
            <span className={r.basis === "default" ? "text-[var(--color-warning)]" : "text-[var(--color-text-muted)]"}>
              {basisText(r.basis)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
