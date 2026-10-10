import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import type { Drawing } from "../types/drawings-boq.types";
import { formatDateTime, formatFileSize } from "../utils/drawings-boq.utils";

interface RunDrawingPickerProps {
  drawings: Drawing[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}

export function RunDrawingPicker({ drawings, selectedIds, onChange, disabled }: RunDrawingPickerProps) {
  const { t } = useTranslation();
  const selected = new Set(selectedIds);

  const nameCount = new Map<string, number>();
  for (const drawing of drawings) {
    const key = drawing.original_filename.trim().toLowerCase();
    nameCount.set(key, (nameCount.get(key) ?? 0) + 1);
  }

  function toggle(id: string) {
    onChange(selected.has(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]);
  }

  return (
    <div className="md:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
          {t("boq.calculationRun.drawingsToCalculate", "Drawings to calculate")}
        </span>
        <div className="flex gap-3 text-[11px] font-semibold text-[var(--color-text-secondary)]">
          <button type="button" disabled={disabled} onClick={() => onChange(drawings.map((d) => d.id))}>
            {t("boq.calculationRun.selectAll", "Select all")}
          </button>
          <button type="button" disabled={disabled} onClick={() => onChange([])}>
            {t("boq.calculationRun.clearSelection", "Clear")}
          </button>
        </div>
      </div>

      {drawings.length === 0 ? (
        <div className="mt-1.5 text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.calculationRun.noEligibleDrawings", "This project has no current, parsed IFC drawing yet.")}
        </div>
      ) : (
        <ul className="mt-1.5 divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
          {drawings.map((drawing) => {
            const duplicate = (nameCount.get(drawing.original_filename.trim().toLowerCase()) ?? 0) > 1;
            return (
              <li key={drawing.id}>
                <label className="flex cursor-pointer items-center gap-3 px-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={selected.has(drawing.id)}
                    disabled={disabled}
                    onChange={() => toggle(drawing.id)}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] font-semibold text-[var(--color-text-primary)]">
                      {drawing.original_filename}
                    </span>
                    <span className="block text-[11px] text-[var(--color-text-muted)]">
                      {[
                        drawing.revision_label,
                        formatFileSize(drawing.file_size_bytes),
                        formatDateTime(drawing.parsed_at ?? drawing.created_at),
                      ].filter(Boolean).join(" · ")}
                    </span>
                  </span>
                  {duplicate ? (
                    <Badge tone="gold">{t("boq.calculationRun.sameNameBadge", "Same file name as another drawing")}</Badge>
                  ) : null}
                </label>
              </li>
            );
          })}
        </ul>
      )}

      {selectedIds.length > 1 ? (
        <p className="mt-2 text-[11.5px] text-[var(--color-warning)]">
          {t(
            "boq.calculationRun.multiDrawingWarning",
            "{{count}} drawings are selected and their quantities will be added together. Select several only when they are parts of one building, never copies of the same model.",
            { count: selectedIds.length },
          )}
        </p>
      ) : null}
    </div>
  );
}
