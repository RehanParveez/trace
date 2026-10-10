import { Toggle } from "../../../organizations/components/OrganizationUi";
import type { RunOptions } from "../types/recalculation.types";
import { useScaleT } from "../utils/useRecalculationT";

interface RunOptionsFieldsProps {
  value: RunOptions;
  onChange: (next: RunOptions) => void;
  disabled?: boolean;
}

export function RunOptionsFields({ value, onChange, disabled = false }: RunOptionsFieldsProps) {
  const t = useScaleT();

  const rows: Array<{ key: keyof RunOptions; label: string; hint: string }> = [
    {
      key: "force_full",
      label: t("scale.options.forceFull", "Recalculate everything"),
      hint: t(
        "scale.options.forceFullHint",
        "By default a run reuses the earlier result for elements that did not change. Turn this on to calculate every element again.",
      ),
    },
    {
      key: "verify",
      label: t("scale.options.verify", "Check against a full calculation"),
      hint: t(
        "scale.options.verifyHint",
        "After a partial update, also run the full calculation and compare. Slower. If they differ, the full result is kept.",
      ),
    },
  ];

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {rows.map((row) => (
        <div
          key={row.key}
          className="flex items-start justify-between gap-3 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3"
        >
          <div className="min-w-0">
            <div className="text-[12px] font-semibold text-[var(--color-text-primary)]">{row.label}</div>
            <div className="mt-1 text-[11px] leading-snug text-[var(--color-text-muted)]">{row.hint}</div>
          </div>
          <Toggle
            checked={value[row.key]}
            disabled={disabled || (row.key === "verify" && value.force_full)}
            label={row.label}
            onChange={() => onChange({ ...value, [row.key]: !value[row.key] })}
          />
        </div>
      ))}
    </div>
  );
}
