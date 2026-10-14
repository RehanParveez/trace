import { useTranslation } from "react-i18next";
import type { DrawingFacts, StructureLevel } from "../types/takeoff.types";
import { marksFrom } from "../utils/check";
import { hasStructure, markNeedsSize, marksText, planViews, scaleText, slabParts, structureLevels } from "../utils/structure";

interface Props {
  facts: DrawingFacts | undefined;
}

function MarkLine({ label, marks }: { label: string; marks: StructureLevel["column_marks"] }) {
  const { t } = useTranslation();
  if (marks.length === 0) return null;
  const unsized = marks.filter(markNeedsSize).length;
  const fromDetail = marksFrom(marks, "DETAIL");
  return (
    <li>
      <span className="font-semibold text-[var(--color-text-primary)]">{label}</span> {marksText(marks)}
      {fromDetail.length > 0 ? <span> · {t("drawings.structure.fromDetail", { defaultValue: "{{marks}}: size from the column detail", marks: fromDetail.join(", ") })}</span> : null}
      {unsized > 0 ? <span className="text-[var(--color-warning)]"> · {t("drawings.structure.noSize", { defaultValue: "{{n}} without a size", n: unsized })}</span> : null}
    </li>
  );
}

function LevelRow({ l }: { l: StructureLevel }) {
  const { t } = useTranslation();
  const slab = slabParts(l);
  return (
    <div className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`structure-${l.key}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-[var(--color-text-primary)]">{l.name}</span>
        <span className="text-[var(--color-text-muted)]">
          {t("drawings.structure.counts", { defaultValue: "{{c}} columns · {{f}} footings · {{b}} beam marks", c: l.columns, f: l.footings, b: l.beams })}
        </span>
      </div>
      <ul className="mt-1 list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
        <MarkLine label={t("drawings.structure.columns", "Columns")} marks={l.column_marks} />
        <MarkLine label={t("drawings.structure.footings", "Footings")} marks={l.footing_marks} />
        <MarkLine label={t("drawings.structure.beams", "Beams")} marks={l.beam_marks} />
        {slab.panels > 0 || slab.thickness ? (
          <li>
            {slab.panels > 0 ? t("drawings.structure.panels", { defaultValue: "{{n}} slab panels", n: slab.panels }) : ""}
            {slab.thickness ? `${slab.panels > 0 ? " · " : ""}${t("drawings.structure.slab", { defaultValue: "slab note {{t}}", t: slab.thickness })}` : ""}
          </li>
        ) : null}
      </ul>
    </div>
  );
}

export function StructureSection({ facts }: Props) {
  const { t } = useTranslation();
  if (!hasStructure(facts)) return null;
  const levels = structureLevels(facts);
  const views = planViews(facts);
  return (
    <div className="space-y-1.5" data-testid="structure-section">
      <div className="font-semibold text-[var(--color-text-primary)]">{t("drawings.structure.title", "Structure by floor")}</div>
      <p className="text-[11px] leading-snug text-[var(--color-text-muted)]">
        {t("drawings.structure.intro", "Columns, footings and beam marks are counted on each structural plan separately, so the same mark on two floors is two lots. Column sizes are measured from the plan; a footing size is taken from the section details and the pairing with its mark is a guess to confirm. Heights and depths are asked for when you accept an item.")}
      </p>
      {levels.map((l) => <LevelRow key={l.key} l={l} />)}
      {views.length > 0 ? (
        <details data-testid="structure-views">
          <summary className="cursor-pointer text-[11px] text-[var(--color-text-muted)]">
            {t("drawings.structure.views", { defaultValue: "{{n}} drawings found on the structural sheet", n: views.length })}
          </summary>
          <ul className="mt-1 list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
            {views.map((v) => (
              <li key={v.key}>
                {v.caption ?? v.key}
                {v.foundation ? ` · ${t("drawings.structure.foundation", "foundation plan")}` : ""}
                {scaleText(v) ? ` · ${t("drawings.structure.scale", { defaultValue: "scale {{s}}", s: scaleText(v) })}` : ""}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
