import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Icon, LoadingState, Panel, PanelHeader, TableShell, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useDeleteSpace, useProjectLevels, useSpaces, useUpdateSpace } from "../hooks/useSpacesSchedules";
import { fmt, mm2ToM2, mmToM, SPACE_CATEGORIES, spaceLabel } from "../utils/drawings-boq.utils";
import type { Drawing } from "../types/drawings-boq.types";
import type { SpaceResponse } from "../types/drawings-boq.types";
import { ConfirmDialog } from "./ConfirmDialog";
import { SpaceDetailDialog } from "./SpaceDetailDialog";
import { SpaceFormDialog } from "./SpaceFormDialog";
import { useTranslation } from "react-i18next";

interface SpacesPanelProps {
  projectId: string;
  drawings: Drawing[];
  canManage: boolean;
  canManageFinish: boolean;
}

const selectCls = "rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12px] text-[var(--color-text-primary)]";
const th = "px-3 py-3 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function SpacesPanel({ projectId, drawings, canManage, canManageFinish }: SpacesPanelProps) {
  const { t } = useTranslation();
  const levels = useProjectLevels(drawings);
  const [levelId, setLevelId] = useState("");
  const [category, setCategory] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [currentOnly, setCurrentOnly] = useState(true);
  const query = useSpaces(projectId, { level_id: levelId || undefined, category: category || undefined, include_inactive: includeInactive, current_only: currentOnly });
  const remove = useDeleteSpace(projectId);
  const update = useUpdateSpace(projectId);
  const { showToast } = useToast();

  const [form, setForm] = useState<{ space?: SpaceResponse } | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [removing, setRemoving] = useState<SpaceResponse | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const spaces = query.data ?? [];
  const levelName = new Map(levels.map((l) => [l.id, l.name]));
  const totalArea = spaces.filter((s) => s.is_active && !s.is_external).reduce((sum, s) => sum + (mm2ToM2(s.net_floor_area_mm2) ?? 0), 0);

  function confirmRemove() {
    if (!removing) return;
    setRemoveError(null);
    remove.mutate(removing.id, {
      onSuccess: () => { showToast({ tone: "success", title: removing.source === "MANUAL" ? t("spaces.deleted", "Space deleted") : t("spaces.hidden", "Space hidden") }); setRemoving(null); },
      onError: (e) => setRemoveError(getApiErrorMessage(e, t("spaces.removeError", "Couldn't remove this space."))),
    });
  }

  function restore(s: SpaceResponse) {
    update.mutate({ spaceId: s.id, payload: { is_active: true } }, {
      onSuccess: () => showToast({ tone: "success", title: t("spaces.restored", "Space restored") }),
      onError: (e) => showToast({ tone: "error", title: t("spaces.restoreError", "Couldn't restore this space"), description: getApiErrorMessage(e, "") }),
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("spaces.eyebrow", "Rooms")}
        title={t("spaces.title", "Spaces and finishes")}
        description={t("spaces.description", "Rooms read from the model, plus any you add by hand. Finishes are measured per room.")}
        action={canManage ? <Button variant="primary" size="sm" onClick={() => setForm({})}><Icon name="plus" size={13} />{t("spaces.add", "Add space")}</Button> : null}
      />

      <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] px-5 py-3">
        <select className={selectCls} value={levelId} onChange={(e) => setLevelId(e.target.value)}>
          <option value="">{t("spaces.allLevels", "All levels")}</option>
          {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <select className={selectCls} value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">{t("spaces.allCategories", "All categories")}</option>
          {SPACE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]"><input type="checkbox" checked={currentOnly} onChange={(e) => setCurrentOnly(e.target.checked)} />{t("spaces.currentOnly", "Current models only")}</label>
        <label className="flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]"><input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />{t("spaces.showInactive", "Show hidden")}</label>
        <span className="ml-auto font-mono text-[11.5px] text-[var(--color-text-muted)]">{spaces.length} · {fmt(totalArea)} m² {t("spaces.internal", "internal")}</span>
      </div>

      {query.isLoading ? (
        <LoadingState label={t("spaces.loading", "Loading spaces…")} />
      ) : query.isError ? (
        <ErrorState title={t("spaces.loadError", "Couldn't load spaces")} onRetry={() => void query.refetch()} />
      ) : spaces.length === 0 ? (
        <EmptyState
          icon="building"
          title={t("spaces.emptyTitle", "No spaces")}
          description={t("spaces.emptyDesc", "Rooms appear after an IFC model with IfcSpace elements is parsed. You can also add them by hand.")}
          action={canManage ? <Button variant="primary" size="sm" onClick={() => setForm({})}>{t("spaces.add", "Add space")}</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[980px] text-left">
            <thead className="bg-[var(--color-surface-muted)]"><tr>
              <th className={th}>{t("spaces.colRoom", "Room")}</th><th className={th}>{t("spaces.colCategory", "Category")}</th><th className={th}>{t("spaces.colLevel", "Level")}</th>
              <th className={`${th} text-right`}>{t("spaces.colArea", "Area m²")}</th><th className={`${th} text-right`}>{t("spaces.colPerimeter", "Perimeter m")}</th><th className={`${th} text-right`}>{t("spaces.colHeight", "Height m")}</th>
              <th className={`${th} text-right`}>{t("spaces.colFinishes", "Finishes")}</th><th className={`${th} text-right`}>{t("spaces.colBoundaries", "Boundaries")}</th>
              <th className={th}>{t("spaces.colStatus", "Status")}</th><th className={`${th} text-right`}>{t("spaces.colActions", "Actions")}</th>
            </tr></thead>

            <tbody>
              {spaces.map((s) => (
                <tr key={s.id} className={`border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)] ${s.is_active ? "" : "opacity-60"}`}>
                  <td className="px-3 py-3">
                    <button type="button" className="text-left" onClick={() => setDetailId(s.id)}>
                      <span className="block text-[13.5px] font-semibold text-[var(--color-text-primary)]">{spaceLabel(s)}</span>
                      {s.long_name ? <span className="block text-[11.5px] text-[var(--color-text-muted)]">{s.long_name}</span> : null}
                    </button>
                  </td>

                  <td className="px-3 py-3 text-[12px] text-[var(--color-text-secondary)]">{s.category}{s.is_external ? <span className="ml-1.5 text-[11px] text-[var(--color-text-muted)]">{t("spaces.external", "external")}</span> : null}</td>
                  <td className="px-3 py-3 text-[12px] text-[var(--color-text-secondary)]">{s.level_id ? levelName.get(s.level_id) ?? "—" : "—"}</td>
                  <td className="px-3 py-3 text-right font-mono text-[12.5px]">{fmt(mm2ToM2(s.net_floor_area_mm2))}</td>
                  <td className="px-3 py-3 text-right font-mono text-[12.5px]">{fmt(mmToM(s.perimeter_mm))}</td>
                  <td className="px-3 py-3 text-right font-mono text-[12.5px]">{fmt(mmToM(s.height_mm))}</td>
                  <td className="px-3 py-3 text-right font-mono text-[12.5px]">{s.finish_count}</td>
                  <td className="px-3 py-3 text-right font-mono text-[12.5px]">{s.boundary_count}</td>
                  <td className="px-3 py-3">

                    <div className="flex flex-wrap gap-1">
                      <Badge tone={s.source === "IFC" ? "blue" : "gold"}>{s.source}</Badge>
                      {s.normalization_status !== "VALID" ? <span title={s.normalization_issues.map((i) => i.message).join("\n")}><Badge tone={s.normalization_status === "INVALID" ? "red" : "gold"}>{s.normalization_status}</Badge></span> : null}
                      {!s.is_active ? <Badge tone="slate">{t("spaces.hiddenBadge", "hidden")}</Badge> : null}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setDetailId(s.id)}>{t("common.open", "Open")}</Button>
                      {canManage ? <Button variant="ghost" size="sm" onClick={() => setForm({ space: s })}>{t("common.edit", "Edit")}</Button> : null}
                      {canManage && s.is_active ? <Button variant="ghost" size="sm" onClick={() => { setRemoveError(null); setRemoving(s); }}>{s.source === "MANUAL" ? t("common.delete", "Delete") : t("spaces.hide", "Hide")}</Button> : null}
                      {canManage && !s.is_active ? <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => restore(s)}>{t("spaces.restore", "Restore")}</Button> : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {form ? <SpaceFormDialog projectId={projectId} space={form.space} levels={levels} onClose={() => setForm(null)} /> : null}
      {detailId ? <SpaceDetailDialog projectId={projectId} spaceId={detailId} drawings={drawings} canManage={canManage} canManageFinish={canManageFinish} onClose={() => setDetailId(null)} /> : null}
      {removing ? (
        <ConfirmDialog
          title={removing.source === "MANUAL" ? t("spaces.deleteTitle", "Delete space") : t("spaces.hideTitle", "Hide space")}
          description={spaceLabel(removing)}
          confirmLabel={remove.isPending ? t("common.saving", "Saving…") : removing.source === "MANUAL" ? t("common.delete", "Delete") : t("spaces.hide", "Hide")}
          pending={remove.isPending}
          error={removeError}
          onConfirm={confirmRemove}
          onClose={() => setRemoving(null)}
        >
          <p className="text-[12.5px] text-[var(--color-text-secondary)]">
            {removing.source === "MANUAL"
              ? t("spaces.deleteBody", "This manual space and its finishes are deleted. Re-run the calculation to update quantities.")
              : t("spaces.hideBody", "This room comes from the model, so it is hidden rather than deleted. You can restore it later.")}
          </p>
        </ConfirmDialog>
      ) : null}
    </Panel>
  );
}
