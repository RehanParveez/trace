import { useMemo, useState } from "react";
import { Badge, Button, EmptyState, ErrorState, LoadingState, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBoundaryCandidates, useSetSpaceBoundaries } from "../hooks/useSpacesSchedules";
import { isBoundaryRole, spaceLabel } from "../utils/drawings-boq.utils";
import type { Drawing, SpaceDetailResponse } from "../types/drawings-boq.types";

import { useTranslation } from "react-i18next";

const MAX_BOUNDARIES = 500;

interface SpaceBoundariesDialogProps {
  projectId: string;
  space: SpaceDetailResponse;
  drawings: Drawing[];
  onClose: () => void;
}

export function SpaceBoundariesDialog({ projectId, space, drawings, onClose }: SpaceBoundariesDialogProps) {
  const { t } = useTranslation();
  const save = useSetSpaceBoundaries(projectId);
  const { showToast } = useToast();
  const models = drawings.filter((d) => d.is_current_revision && d.format === "IFC" && d.status === "PARSED");
  const [drawingId, setDrawingId] = useState(space.drawing_id ?? models[0]?.id ?? "");
  const candidates = useBoundaryCandidates(drawingId || undefined);
  const [selected, setSelected] = useState<Set<string>>(() => new Set(space.boundaries.map((b) => b.element_id)));
  const [search, setSearch] = useState("");
  const [allRoles, setAllRoles] = useState(false);
  const [sameLevel, setSameLevel] = useState(Boolean(space.level_id));
  const [error, setError] = useState<string | null>(null);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (candidates.data ?? []).filter(
      (c) =>
        (allRoles || isBoundaryRole(c.structural_role) || selected.has(c.id)) &&
        (!sameLevel || !space.level_id || c.level_id === space.level_id || selected.has(c.id)) &&
        (!q || `${c.name ?? ""} ${c.ifc_type} ${c.structural_role ?? ""}`.toLowerCase().includes(q)),
    );
  }, [candidates.data, search, allRoles, sameLevel, selected, space.level_id]);

  const toggle = (id: string) => setSelected((cur) => { const n = new Set(cur); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const tooMany = selected.size > MAX_BOUNDARIES;

  function submit() {
    setError(null);
    save.mutate({ spaceId: space.id, elementIds: [...selected] }, {
      onSuccess: (r) => { onClose(); showToast({ tone: "success", title: t("spaces.boundaries.saved", "{{n}} boundary element(s) saved", { n: r.boundary_count }) }); },
      onError: (e) => setError(getApiErrorMessage(e, t("spaces.boundaries.error", "Couldn't save the boundaries."))),
    });
  }

  return (
    <Modal title={t("spaces.boundaries.title", "Room boundaries")} description={spaceLabel(space)} onClose={onClose} wide>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          {models.length > 1 || !space.drawing_id ? (
            <select className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12px]" value={drawingId} onChange={(e) => setDrawingId(e.target.value)}>
              {models.map((d) => <option key={d.id} value={d.id}>{d.original_filename}</option>)}
            </select>
          ) : null}
          <input className="min-w-[180px] flex-1 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12px]" placeholder={t("spaces.boundaries.search", "Search name, type or role")} value={search} onChange={(e) => setSearch(e.target.value)} />
          {space.level_id ? <label className="flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]"><input type="checkbox" checked={sameLevel} onChange={(e) => setSameLevel(e.target.checked)} />{t("spaces.boundaries.sameLevel", "Same level only")}</label> : null}
          <label className="flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]"><input type="checkbox" checked={allRoles} onChange={(e) => setAllRoles(e.target.checked)} />{t("spaces.boundaries.allRoles", "All element types")}</label>
          <Badge tone={tooMany ? "red" : "blue"}>{selected.size} / {MAX_BOUNDARIES}</Badge>
        </div>

        {models.length === 0 ? (
          <EmptyState icon="info" title={t("spaces.boundaries.noModel", "No parsed model")} description={t("spaces.boundaries.noModelDesc", "Upload and parse an IFC model to pick boundary elements.")} />
        ) : candidates.isLoading ? (
          <LoadingState label={t("spaces.boundaries.loading", "Loading elements…")} />
        ) : candidates.isError ? (
          <ErrorState title={t("spaces.boundaries.loadError", "Couldn't load elements")} onRetry={() => void candidates.refetch()} />
        ) : (
          <div className="max-h-[50vh] overflow-y-auto rounded-[8px] border border-[var(--color-border)]">
            {rows.length === 0 ? (
              <div className="px-4 py-6 text-center text-[12.5px] text-[var(--color-text-muted)]">{t("spaces.boundaries.none", "No elements match.")}</div>
            ) : (
              <ul className="divide-y divide-[var(--color-border)]">
                {rows.map((c) => (
                  <li key={c.id}>
                    <label className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-[var(--color-surface-muted)]">
                      <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} />
                      <span className="flex-1 truncate text-[12.5px] text-[var(--color-text-primary)]">{c.name ?? c.ifc_type}</span>
                      <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{c.structural_role ?? c.ifc_type}</span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={save.isPending}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" onClick={submit} disabled={save.isPending || tooMany}>{save.isPending ? t("common.saving", "Saving…") : t("common.save", "Save")}</Button>
        </div>
      </div>
    </Modal>
  );
}
