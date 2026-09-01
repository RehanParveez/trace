import type { BOQVersion } from "../types/drawings-boq.types";

interface BOQVersionTabsProps {
  versions: BOQVersion[];
  selectedId: string | undefined;
  onSelect: (versionId: string) => void;
}

export function BOQVersionTabs({ versions, selectedId, onSelect }: BOQVersionTabsProps) {
  if (versions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 border-b border-[#e1d5bc] p-4">
      {versions.map((version) => (
        <button
          key={version.id}
          type="button"
          onClick={() => onSelect(version.id)}
          className={`rounded-[7px] border px-3 py-1.5 text-[10.5px] font-semibold transition ${
            selectedId === version.id
              ? "border-[#d9a441] bg-[#fbefd9] text-[#76531a]"
              : version.status === "SUPERSEDED"
                ? "border-[#e1d5bc] bg-[#f5efe3] text-[#a2957c] hover:border-[#cdbd9c]"
                : "border-[#e1d5bc] bg-white text-[#6b6152] hover:border-[#cdbd9c]"
          }`}
        >
          {version.label}
          {version.status === "SUPERSEDED" ? <span className="ml-1.5 text-[9px] font-normal italic">superseded</span> : null}
        </button>
      ))}
    </div>
  );
}