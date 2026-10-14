import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { BOQItemSpec, LedgerTrace } from "../types/drawings-boq.types";
import { derivedBasisRows, derivedHasAssumption, derivedPdfSourceView, isDerivedSpec } from "../utils/derived";
import type { DerivedBasis } from "../utils/derived";

function useBasisText(): (basis: DerivedBasis | null) => string {
  const { t } = useTranslation();
  return (basis) => {
    if (basis === "user") return t("boq.derived.basis.user", "given");
    if (basis === "convention") return t("boq.derived.basis.convention", "set on the convention");
    if (basis === "default") return t("boq.derived.basis.default", "assumed");
    if (basis === "claim") return t("boq.derived.basis.claim", "reference level for the footing depth");
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

export function DerivedPdfSource({ trace }: { trace?: LedgerTrace | null }) {
  const { t } = useTranslation();
  const view = derivedPdfSourceView(trace);
  if (!view) return null;
  return (
    <div className="space-y-1 rounded-[8px] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {t("boq.derived.pdfSourceTitle", "Read from the drawing")}
      </div>
      <p className="text-[12px] text-[var(--color-text-secondary)]">
        {t("boq.derived.pdfSourceText", {
          defaultValue:
            "Footing {{tag}} ({{instance}} of {{instances}}) on sheet {{page}}, placed at its mark. Size {{l}} x {{w}} mm, {{d}} mm thick, bottom {{b}} mm below natural ground.",
          tag: view.tag || "—",
          instance: view.instance,
          instances: view.instances,
          page: view.page,
          l: view.lengthMm,
          w: view.widthMm,
          d: view.thicknessMm,
          b: view.bottomBelowGroundMm,
        })}
      </p>
      <p className="text-[11px] text-[var(--color-warning)]">
        {t("boq.derived.pdfSourceCaution", "The mark stands in for the drawn outline, so footings close together share a trench only approximately.")}
      </p>
    </div>
  );
}

