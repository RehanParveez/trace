import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { CalculationRun, Drawing } from "../types/drawings-boq.types";
import { formatFileSize } from "../utils/drawings-boq.utils";
import { resolveRunScope, scopeEntryLabel, scopeNeedsAttention } from "../utils/run-scope";

interface RunScopeProps {
  run: Pick<CalculationRun, "drawing_revision_ids" | "scope_drawings" | "scope_overlaps"> | null | undefined;
  drawings: Drawing[] | null;
  label?: string;
}

export function RunScope({ run, drawings, label }: RunScopeProps) {
  const { t } = useTranslation();
  const entries = resolveRunScope(run, drawings);

  if (entries.length === 0) {
    return null;
  }

  const attention = scopeNeedsAttention(entries);
  const unknownLabel = t("boq.sourceDrawings.unknown", "Unknown drawing");

  return (
    <div className="space-y-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
          {label ?? t("boq.sourceDrawings.label", "Built from")}
        </span>
        {entries.length > 1 ? (
          <Badge tone="gold">
            {t("boq.sourceDrawings.combined", "{{count}} drawings combined", { count: entries.length })}
          </Badge>
        ) : null}
      </div>

      <ul className="space-y-1">
        {entries.map((entry) => (
          <li key={entry.id} className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-semibold text-[var(--color-text-primary)]">
              {scopeEntryLabel(entry, unknownLabel)}
            </span>
            <span className="text-[11px] text-[var(--color-text-muted)]">
              {[entry.format, entry.fileSizeBytes !== null ? formatFileSize(entry.fileSizeBytes) : null]
                .filter(Boolean)
                .join(" · ")}
            </span>
            {entry.state === "replaced" ? (
              <Badge tone="gold">{t("boq.sourceDrawings.replaced", "Replaced by a newer revision")}</Badge>
            ) : null}
            {entry.state === "removed" ? (
              <Badge tone="red">{t("boq.sourceDrawings.removed", "No longer in this project")}</Badge>
            ) : null}
          </li>
        ))}
      </ul>

      {attention ? (
        <p className="text-[11.5px] text-[var(--color-warning)]">
          {t(
            "boq.sourceDrawings.changedNote",
            "Some drawings behind this run have been replaced or removed since it was calculated. The quantities are still those of the original files; recalculate to use the latest revision.",
          )}
        </p>
            ) : null}

      {(run?.scope_overlaps ?? []).length > 0 ? (
        <div className="space-y-1 text-[11.5px] text-[var(--color-warning)]">
          <p>
            {t(
              "boq.sourceDrawings.overlapNote",
              "These drawings share model elements and were calculated together at your request. The shared elements may be counted in each drawing.",
            )}
          </p>
          <ul className="space-y-0.5">
            {(run?.scope_overlaps ?? []).map((o) => (
              <li key={`${o.drawing_a_id}-${o.drawing_b_id}`}>
                {t("boq.sourceDrawings.overlapPair", "{{a}} and {{b}}: {{count}} shared elements", {
                  a: o.drawing_a_name, b: o.drawing_b_name, count: o.shared_elements,
                })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
