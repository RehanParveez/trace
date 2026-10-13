import type { CalculationRun, Drawing } from "../types/drawings-boq.types";

export type RunScopeState = "current" | "replaced" | "removed" | "unknown";

export interface RunScopeEntry {
  id: string;
  filename: string | null;
  format: string | null;
  revisionLabel: string | null;
  fileSizeBytes: number | null;
  state: RunScopeState;
}

type RunLike = Pick<CalculationRun, "drawing_revision_ids" | "scope_drawings">;

function byName(a: RunScopeEntry, b: RunScopeEntry): number {
  if ((a.filename === null) !== (b.filename === null)) {
    return a.filename === null ? 1 : -1;
  }
  const left = (a.filename ?? "").toLowerCase();
  const right = (b.filename ?? "").toLowerCase();
  return left < right ? -1 : left > right ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

export function resolveRunScope(
  run: RunLike | null | undefined,
  drawings: readonly Drawing[] | null,
): RunScopeEntry[] {
  if (!run) {
    return [];
  }
  const snapshot = new Map((run.scope_drawings ?? []).map((entry) => [entry.drawing_id, entry]));
  const ids = run.drawing_revision_ids?.length
    ? run.drawing_revision_ids
    : [...snapshot.keys()];
  const live = drawings ? new Map(drawings.map((drawing) => [drawing.id, drawing])) : null;

  return ids
    .map((id): RunScopeEntry => {
      const recorded = snapshot.get(id);
      const drawing = live?.get(id);
      let state: RunScopeState = "unknown";
      if (live) {
        state = !drawing ? "removed" : drawing.is_current_revision ? "current" : "replaced";
      }
      return {
        id,
        filename: recorded?.filename ?? drawing?.original_filename ?? null,
        format: recorded?.format ?? drawing?.format ?? null,
        revisionLabel: recorded ? recorded.revision_label : (drawing?.revision_label ?? null),
        fileSizeBytes: recorded?.file_size_bytes ?? drawing?.file_size_bytes ?? null,
        state,
      };
    })
    .sort(byName);
}

export function scopeNeedsAttention(entries: readonly RunScopeEntry[]): boolean {
  return entries.some((entry) => entry.state === "replaced" || entry.state === "removed");
}

export function scopeEntryLabel(entry: RunScopeEntry, unknownLabel: string): string {
  if (!entry.filename) {
    return `${unknownLabel} (${entry.id.slice(0, 8)})`;
  }
  return entry.revisionLabel ? `${entry.filename} (${entry.revisionLabel})` : entry.filename;
}
