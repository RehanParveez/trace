import type { BOQVersion } from "../types/drawings-boq.types";

interface BOQVersionTabsProps {
  versions: BOQVersion[];
  selectedId: string | undefined;
  onSelect: (versionId: string) => void;
}

export function BOQVersionTabs({ versions, selectedId, onSelect }: BOQVersionTabsProps) {
  if (versions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] p-4">
      {versions.map((version) => (
        <button
          key={version.id}
          type="button"
          onClick={() => onSelect(version.id)}
          className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${
            selectedId === version.id
              ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
              : version.status === "SUPERSEDED"
                ? "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]"
                : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"
          }`}
        >
          {version.label}
          {version.status === "SUPERSEDED" ? <span className="ml-1.5 text-[10px] font-normal italic">superseded</span> : null}
        </button>
      ))}
    </div>
  );
}