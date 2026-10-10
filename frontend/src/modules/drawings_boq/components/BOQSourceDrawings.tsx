import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import { useCalculationRun } from "../hooks";
import type { Drawing } from "../types/drawings-boq.types";

interface BOQSourceDrawingsProps {
  runId: string | null | undefined;
  drawings: Drawing[];
}

export function BOQSourceDrawings({ runId, drawings }: BOQSourceDrawingsProps) {
  const { t } = useTranslation();
  const runQuery = useCalculationRun(runId ?? undefined);
  const ids = runQuery.data?.drawing_revision_ids ?? [];

  if (!runId || ids.length === 0) {
    return null;
  }

  const byId = new Map(drawings.map((d) => [d.id, d]));
  const label = (id: string) => {
    const d = byId.get(id);
    return d ? `${d.original_filename}${d.revision_label ? ` (${d.revision_label})` : ""}` : id.slice(0, 8);
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
      <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
        {t("boq.sourceDrawings.label", "Built from")}
      </span>
      <span className="font-semibold text-[var(--color-text-primary)]">{ids.map(label).join(", ")}</span>
      {ids.length > 1 ? (
        <Badge tone="gold">
          {t("boq.sourceDrawings.combined", "{{count}} drawings combined", { count: ids.length })}
        </Badge>
      ) : null}
    </div>
  );
}
