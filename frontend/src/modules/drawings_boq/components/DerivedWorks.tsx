import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { BOQItemSpec, LedgerTrace } from "../types/drawings-boq.types";
import { derivedBasisRows, derivedHasAssumption, derivedPdfSourceView, formworkSourceView, isDerivedSpec, isFormworkSpec, isSteelSpec, steelSourceView } from "../utils/derived";
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
    isFormworkSpec(spec)
      ? t("boq.derived.badgeHintFormwork", "Not drawn in the model. Worked out from the concrete members read from the drawing.")
      : isSteelSpec(spec)
      ? t("boq.derived.badgeHintSteel", "Not drawn in the model. Worked out from the bars printed on the drawing.")
      : t("boq.derived.badgeHint", "Not drawn in the model. Worked out from the foundations."),
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

export function DerivedFormworkSource({ trace }: { trace?: LedgerTrace | null }) {
  const { t } = useTranslation();
  const view = formworkSourceView(trace);
  if (!view) return null;
  return (
    <div className="space-y-1 rounded-[8px] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {t("boq.derived.formworkSourceTitle", "Read from the drawing")}
      </div>
      <p className="text-[12px] text-[var(--color-text-secondary)]">
        {t("boq.derived.formworkSourceText", {
          defaultValue: "{{category}} {{tag}} ({{instance}} of {{instances}}) on sheet {{page}}. Size {{l}} x {{w}} x {{d}} mm.",
          category: t(`boq.derived.category.${view.category}`, view.category),
          tag: view.tag || "—",
          instance: view.instance,
          instances: view.instances,
          page: view.page,
          l: view.lengthMm,
          w: view.widthMm,
          d: view.depthMm,
        })}
      </p>
      <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
        {view.faces.map((f) => (
          <li key={f.name} className="flex flex-wrap items-baseline gap-2">
            <span>{t(`boq.derived.face.${f.name}`, f.name)}</span>
            <span className="font-mono font-semibold text-[var(--color-text-primary)]">{f.m2} m²</span>
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-[var(--color-warning)]">
        {t("boq.derived.formworkContact", "Gross area of the member. Faces that touch other concrete are not taken off.")}
      {t("boq.derived.formworkContact", "Gross area of the member. Faces that touch other concrete are not taken off.")}
      </p>
    </div>
  );
}

export function DerivedSteelSource({ trace }: { trace?: LedgerTrace | null }) {
  const { t } = useTranslation();
  const view = steelSourceView(trace);
  if (!view) return null;
  return (
    <div className="space-y-1 rounded-[8px] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {t("boq.derived.steelSourceTitle", "Bars printed on the drawing")}
      </div>
      <p className="text-[12px] text-[var(--color-text-secondary)]">
        {t("boq.derived.steelSourceText", {
          defaultValue: "{{category}} {{tag}} ({{instance}} of {{instances}}) on sheet {{page}}. Size {{l}} x {{w}} x {{d}} mm.",
          category: t(`boq.derived.category.${view.category}`, view.category),
          tag: view.tag || "—",
          instance: view.instance,
          instances: view.instances,
          page: view.page,
          l: view.lengthMm,
          w: view.widthMm,
          d: view.depthMm,
        })}
      </p>
      <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
        {view.lines.map((l, i) => (
          <li key={`${l.kind}-${l.role}-${i}`} className="flex flex-wrap items-baseline gap-2">
            <span>
              {t(`boq.derived.steelLine.${l.kind}`, {
                defaultValue: l.kind === "bars" ? "{{n}} {{size}} {{role}}, {{cut}} m each" : l.kind === "rings" ? "Rings {{size}}: {{n}} of {{cut}} m" : "Mesh {{size}} {{role}}: {{n}} bars of {{cut}} m",
                n: l.count,
                size: l.size,
                role: t(`boq.derived.steelRole.${l.role}`, l.role),
                cut: l.cutLengthM,
              })}
            </span>
            <span className="font-mono font-semibold text-[var(--color-text-primary)]">{l.kg} kg</span>
          </li>
        ))}
      </ul>
      {view.concreteM3 && view.bareKg && Number(view.concreteM3) > 0 ? (
        <p className="text-[11px] text-[var(--color-text-muted)]" data-testid="steel-intensity">
          {t("boq.derived.steelIntensity", {
            defaultValue: "{{kg}} kg of bars in {{m3}} m3 of concrete: {{per}} kg per m3",
            kg: view.bareKg,
            m3: view.concreteM3,
            per: (Number(view.bareKg) / Number(view.concreteM3)).toFixed(1),
          })}
        </p>
      ) : null}
      <p className="text-[11px] text-[var(--color-warning)]">
        {t("boq.derived.steelLap", "Weight of the bars and rings as printed. Laps, chairs, binding wire and wastage are not added.")}
        {view.wastagePct && Number(view.wastagePct) > 0 ? ` ${t("boq.derived.steelWastage", { defaultValue: "Includes {{pct}} percent wastage.", pct: view.wastagePct })}` : ""}
      </p>
    </div>
  );
}
