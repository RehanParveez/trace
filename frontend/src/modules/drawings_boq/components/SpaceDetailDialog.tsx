import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Field, inputClass, LoadingState, Modal, TableShell, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useDeleteSpaceFinish, useSpaceDetail, useUpsertSpaceFinish } from "../hooks/useSpacesSchedules";
import { fmt, mm2ToM2, mmToM, spaceLabel, suggestFinishWorkItem, SURFACES, SURFACE_UNIT, WORK_ITEM_SUGGESTIONS } from "../utils/drawings-boq.utils";
import type { Drawing } from "../types/drawings-boq.types";
import type { SpaceFinishResponse, Surface } from "../types/drawings-boq.types";
import { SpaceBoundariesDialog } from "./SpaceBoundariesDialog";
import { SpaceFinishPreview } from "./SpaceFinishPreview";
import { useTranslation } from "react-i18next";

interface SpaceDetailDialogProps {
  projectId: string;
  spaceId: string;
  drawings: Drawing[];
  canManage: boolean;
  canManageFinish: boolean;
  onClose: () => void;
}

type Tab = "finishes" | "boundaries" | "preview";
const th = "px-3 py-2.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const selectCls = "w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12.5px]";

export function SpaceDetailDialog({ projectId, spaceId, drawings, canManage, canManageFinish, onClose }: SpaceDetailDialogProps) {
  const { t } = useTranslation();
  const query = useSpaceDetail(spaceId);
  const upsert = useUpsertSpaceFinish(projectId);
  const remove = useDeleteSpaceFinish(projectId);
  const { showToast } = useToast();
  const space = query.data;

  const [tab, setTab] = useState<Tab>("finishes");
  const [surface, setSurface] = useState<Surface>("FLOOR");
  const [workItem, setWorkItem] = useState("FIN-FLOOR");
  const [workItemTouched, setWorkItemTouched] = useState(false);
  const [finishName, setFinishName] = useState("");
  const [height, setHeight] = useState("");
  const [deduct, setDeduct] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingBoundaries, setEditingBoundaries] = useState(false);

  const tabCls = (a: boolean) =>
    `rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${a ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"}`;

  function pickSurface(s: Surface) {
    setSurface(s);
    if (!workItemTouched) setWorkItem(suggestFinishWorkItem(s, finishName) ?? "");
  }

  function edit(f: SpaceFinishResponse) {
    setSurface(f.surface); setWorkItem(f.work_item_code); setWorkItemTouched(true);
    setFinishName(f.finish_name ?? ""); setHeight(f.height_mm !== null ? String(Number(f.height_mm)) : ""); setError(null);
    setDeduct(f.deduct_openings ?? true);
  }

  function submit() {
    setError(null);
    upsert.mutate(
      { spaceId, payload: { surface, work_item_code: workItem.trim(), finish_name: finishName.trim() || null, height_mm: height === "" ? null : Number(height), deduct_openings: deduct } },
      {
        onSuccess: () => { showToast({ tone: "success", title: t("spaces.finish.saved", "Finish saved") }); setFinishName(""); setHeight(""); setDeduct(true); },
        onError: (e) => setError(getApiErrorMessage(e, t("spaces.finish.error", "Couldn't save this finish."))),
      },
    );
  }

  function removeFinish(f: SpaceFinishResponse) {
    remove.mutate({ finishId: f.id, spaceId }, {
      onSuccess: () => showToast({ tone: "success", title: t("spaces.finish.removed", "Finish removed") }),
      onError: (e) => showToast({ tone: "error", title: t("spaces.finish.removeError", "Couldn't remove this finish"), description: getApiErrorMessage(e, "") }),
    });
  }

  return (
    <Modal title={space ? spaceLabel(space) : t("spaces.detail.title", "Space")} description={space?.long_name ?? space?.usage_text ?? undefined} onClose={onClose} wide>
      {query.isLoading ? (
        <LoadingState label={t("spaces.detail.loading", "Loading space…")} />
      ) : query.isError || !space ? (
        <ErrorState title={t("spaces.detail.loadError", "Couldn't load this space")} onRetry={() => void query.refetch()} />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-[12px] text-[var(--color-text-secondary)]">
            <Badge tone="slate">{space.category}</Badge>
            <Badge tone={space.source === "IFC" ? "blue" : "gold"}>{space.source}</Badge>
            {space.is_external ? <Badge tone="blue">{t("spaces.external", "External")}</Badge> : null}
            {!space.is_active ? <Badge tone="red">{t("spaces.inactive", "Inactive")}</Badge> : null}
            <span className="font-mono">{fmt(mm2ToM2(space.net_floor_area_mm2))} m²</span>
            <span className="font-mono">{fmt(mmToM(space.perimeter_mm))} m {t("spaces.perimeterShort", "perimeter")}</span>
            <span className="font-mono">{fmt(mmToM(space.height_mm))} m {t("spaces.heightShort", "high")}</span>
          </div>

          {space.normalization_issues.length > 0 ? (
            <ul className="space-y-1 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">
              {space.normalization_issues.map((i, k) => <li key={`${i.code}-${k}`}><span className="font-mono">{i.code}</span>: {i.message}</li>)}
            </ul>
          ) : null}

          <div className="flex gap-2">
            <button type="button" className={tabCls(tab === "finishes")} onClick={() => setTab("finishes")}>{t("spaces.tab.finishes", "Finishes")} ({space.finishes.filter((f) => f.is_active).length})</button>
            <button type="button" className={tabCls(tab === "boundaries")} onClick={() => setTab("boundaries")}>{t("spaces.tab.boundaries", "Boundaries")} ({space.boundaries.length})</button>
            <button type="button" className={tabCls(tab === "preview")} onClick={() => setTab("preview")}>{t("spaces.tab.preview", "Preview")}</button>
          </div>

          {tab === "finishes" ? (
            <div className="space-y-4">
              {space.finishes.length === 0 ? (
                <EmptyState icon="info" title={t("spaces.finish.emptyTitle", "No finishes")} description={t("spaces.finish.emptyDesc", "Add a finish, import a finish schedule, or rely on rule-set defaults.")} />
              ) : (
                <TableShell>
                  <table className="w-full min-w-[720px] text-left">
                    <thead className="bg-[var(--color-surface-muted)]"><tr>
                      <th className={th}>Surface</th><th className={th}>Work item</th><th className={th}>Finish</th><th className={`${th} text-right`}>Height mm</th>
                      <th className={th}>Openings</th>
                      <th className={th}>Source</th><th className={`${th} text-right`}>Confidence</th><th className={th}>Review</th>{canManageFinish ? <th className={`${th} text-right`}>Actions</th> : null}
                    </tr></thead>
                    <tbody>
                      {space.finishes.map((f) => (
                        <tr key={f.id} className={`border-t border-[var(--color-border)] ${f.is_active ? "" : "opacity-50"}`}>
                          <td className="px-3 py-2.5 text-[12.5px] font-semibold">{f.surface}</td>
                          <td className="px-3 py-2.5 font-mono text-[12px]">{f.work_item_code}</td>
                          <td className="px-3 py-2.5 text-[12.5px] text-[var(--color-text-secondary)]">{f.finish_name ?? "—"}</td>
                          <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{f.height_mm !== null ? Number(f.height_mm) : "—"}</td>
                          <td className="px-3 py-2.5 text-[12px]">
                            {f.surface === "FLOOR" || f.surface === "CEILING"
                              ? "—"
                              : f.deduct_openings ? t("common.yes", "Yes") : t("common.no", "No")}
                          </td>
                          <td className="px-3 py-2.5"><Badge tone={f.source === "MANUAL" ? "blue" : "slate"}>{f.source}</Badge></td>
                          <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{Math.round(Number(f.confidence) * 100)}%</td>
                          <td className="px-3 py-2.5"><Badge tone={f.review_status === "OK" ? "green" : "gold"}>{f.review_status}</Badge>{!f.is_active ? <span className="ml-1.5 text-[11px] text-[var(--color-text-muted)]">{t("spaces.inactive", "inactive")}</span> : null}</td>
                          {canManageFinish ? (
                            <td className="px-3 py-2.5 text-right">
                              <div className="flex justify-end gap-2">
                                <Button variant="ghost" size="sm" onClick={() => edit(f)}>{t("common.edit", "Edit")}</Button>
                                {f.is_active ? <Button variant="ghost" size="sm" disabled={remove.isPending} onClick={() => removeFinish(f)}>{t("common.remove", "Remove")}</Button> : null}
                              </div>
                            </td>
                          ) : null}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableShell>
              )}

              {canManageFinish ? (
                <div className="space-y-3 border-t border-[var(--color-border)] pt-4">
                  <div className="text-[12px] font-semibold text-[var(--color-text-primary)]">{t("spaces.finish.setTitle", "Set a finish")}</div>
                  <div className="grid gap-3 sm:grid-cols-4">
                    <Field label={t("spaces.finish.surface", "Surface")}>
                      <select className={selectCls} value={surface} onChange={(e) => pickSurface(e.target.value as Surface)}>{SURFACES.map((s) => <option key={s} value={s}>{s}</option>)}</select>
                    </Field>
                    <Field label={t("spaces.finish.workItem", "Work item code")}>
                      <input className={inputClass} list="space-finish-work-items" value={workItem} onChange={(e) => { setWorkItem(e.target.value); setWorkItemTouched(true); }} />
                      <datalist id="space-finish-work-items">{WORK_ITEM_SUGGESTIONS.filter((c) => c.startsWith("FIN-")).map((c) => <option key={c} value={c} />)}</datalist>
                    </Field>
                    <Field label={t("spaces.finish.name", "Finish name")}><input className={inputClass} value={finishName} maxLength={200} onChange={(e) => setFinishName(e.target.value)} /></Field>
                    <Field label={t("spaces.finish.height", "Height (mm, optional)")}><input className={inputClass} type="number" step="any" min="0" value={height} onChange={(e) => setHeight(e.target.value)} /></Field>
                  </div>
                  <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("spaces.finish.unitHint", "{{surface}} finishes are measured in {{unit}}. The work item must use the same unit.", { surface: surface[0] + surface.slice(1).toLowerCase(), unit: SURFACE_UNIT[surface] === "m2" ? "m²" : "m" })}</p>
                  <label className="flex items-center gap-2 text-[12.5px] text-[var(--color-text-secondary)]">
                    <input
                      type="checkbox"
                      checked={deduct && surface !== "FLOOR" && surface !== "CEILING"}
                      disabled={surface === "FLOOR" || surface === "CEILING"}
                      onChange={(e) => setDeduct(e.target.checked)}
                    />
                    {t("spaces.finish.deductOpenings", "Deduct doors and windows")}
                  </label>
                  {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
                  <div className="flex justify-end">
                    <Button variant="primary" onClick={submit} disabled={upsert.isPending || !workItem.trim() || (height !== "" && !(Number(height) > 0))}>{upsert.isPending ? t("common.saving", "Saving…") : t("spaces.finish.save", "Save finish")}</Button>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {tab === "boundaries" ? (
            <div className="space-y-3">
              {canManage ? <div className="flex justify-end"><Button variant="primary" size="sm" onClick={() => setEditingBoundaries(true)}>{t("spaces.boundaries.edit", "Edit boundaries")}</Button></div> : null}
              {space.boundaries.length === 0 ? (
                <EmptyState icon="info" title={t("spaces.boundaries.emptyTitle", "No boundary elements")} description={t("spaces.boundaries.emptyDesc", "Wall finishes and opening deductions need the walls, doors and windows around this room.")} />
              ) : (
                <TableShell>
                  <table className="w-full min-w-[560px] text-left">
                    <thead className="bg-[var(--color-surface-muted)]"><tr><th className={th}>Element</th><th className={th}>Role</th><th className={th}>Kind</th><th className={th}>Side</th><th className={th}>Source</th></tr></thead>
                    <tbody>
                      {space.boundaries.map((b) => (
                        <tr key={b.element_id} className="border-t border-[var(--color-border)]">
                          <td className="px-3 py-2.5 text-[12.5px]">{b.name ?? b.ifc_type}</td>
                          <td className="px-3 py-2.5 font-mono text-[11.5px] text-[var(--color-text-secondary)]">{b.structural_role ?? b.ifc_type}</td>
                          <td className="px-3 py-2.5 text-[12px]">{b.boundary_kind}</td>
                          <td className="px-3 py-2.5 text-[12px]">{b.side}</td>
                          <td className="px-3 py-2.5"><Badge tone={b.source === "IFC" ? "blue" : "slate"}>{b.source}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableShell>
              )}
            </div>
          ) : null}

          {tab === "preview" ? <SpaceFinishPreview spaceId={spaceId} /> : null}

          {editingBoundaries ? <SpaceBoundariesDialog projectId={projectId} space={space} drawings={drawings} onClose={() => setEditingBoundaries(false)} /> : null}
        </div>
      )}
    </Modal>
  );
}