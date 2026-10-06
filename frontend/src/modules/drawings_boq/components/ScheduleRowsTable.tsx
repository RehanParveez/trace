import { useState } from "react";
import { Badge, Button, TableShell } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useUpdateScheduleRow } from "../hooks/useSpacesSchedules";
import { fmt, isLinkedFinish, ROW_CONFIDENCE_REVIEW, rowConfirmBlocker, rowTone, spaceLabel, SURFACES, WORK_ITEM_SUGGESTIONS } from "../utils/drawings-boq.utils";
import type { LevelOption, RowDecision, ScheduleRowResponse, ScheduleRowUpdateRequest, SpaceResponse, Surface } from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

interface ScheduleRowsTableProps {
  importId: string;
  rows: ScheduleRowResponse[];
  editable: boolean;
  isFinishSchedule: boolean;
  spaces: SpaceResponse[];
  levels: LevelOption[];
  selected: Set<string>;
  onToggle: (rowId: string) => void;
  onToggleAll: (checked: boolean) => void;
  onNotice: (message: string | null) => void;
}

const th = "px-3 py-3 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const cls = "w-full rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12.5px] outline-none focus:border-[var(--color-trace-gold-dark)]";

export function ScheduleRowsTable({ importId, rows, editable, isFinishSchedule, spaces, levels, selected, onToggle, onToggleAll, onNotice }: ScheduleRowsTableProps) {
  const { t } = useTranslation();
  const update = useUpdateScheduleRow(importId);
  const [editingId, setEditingId] = useState<string | null>(null);
  const spaceName = new Map(spaces.map((s) => [s.id, spaceLabel(s)]));
  const levelName = new Map(levels.map((l) => [l.id, l.name]));

  function decide(row: ScheduleRowResponse, decision: RowDecision) {
    onNotice(null);
    update.mutate({ rowId: row.id, payload: { review_status: decision } }, {
      onError: (e) => onNotice(`${t("schedules.row", "Row")} ${row.row_no}: ${getApiErrorMessage(e, t("schedules.rowError", "couldn't update this row."))}`),
    });
  }

  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));
  const cols = 11 + (isFinishSchedule ? 2 : 0);

  return (
    <TableShell>
      <datalist id="schedule-work-items">{WORK_ITEM_SUGGESTIONS.map((c) => <option key={c} value={c} />)}</datalist>
      <table className="w-full min-w-[1180px] text-left">
        <thead className="bg-[var(--color-surface-muted)]"><tr>
          {editable ? <th className={th}><input type="checkbox" checked={allSelected} onChange={(e) => onToggleAll(e.target.checked)} /></th> : null}
          <th className={th}>#</th><th className={th}>{t("schedules.colMark", "Mark")}</th><th className={th}>{t("schedules.colDescription", "Description")}</th><th className={th}>{t("schedules.colLocation", "Location")}</th>
          {isFinishSchedule ? <><th className={th}>{t("schedules.colSurface", "Surface")}</th><th className={th}>{t("schedules.colRoom", "Room")}</th></> : null}
          <th className={`${th} text-right`}>{t("schedules.colQty", "Qty")}</th><th className={th}>{t("schedules.colUnit", "Unit")}</th><th className={`${th} text-right`}>{t("schedules.colSize", "W×H mm")}</th>
          <th className={th}>{t("schedules.colWorkItem", "Work item")}</th><th className={`${th} text-right`}>{t("schedules.colMatched", "In model")}</th>
          <th className={th}>{t("schedules.colStatus", "Status")}</th><th className={`${th} text-right`}>{t("schedules.colActions", "Actions")}</th>
        </tr></thead>
        <tbody>
          {rows.map((row) =>
            editingId === row.id ? (
              <RowEditor key={row.id} row={row} cols={cols} isFinishSchedule={isFinishSchedule} spaces={spaces} levels={levels} saving={update.isPending}
                onCancel={() => setEditingId(null)}
                onSave={(payload) => {
                  onNotice(null);
                  update.mutate({ rowId: row.id, payload }, {
                    onSuccess: () => setEditingId(null),
                    onError: (e) => onNotice(`${t("schedules.row", "Row")} ${row.row_no}: ${getApiErrorMessage(e, t("schedules.rowError", "couldn't update this row."))}`),
                  });
                }} />
            ) : (
              <tr key={row.id} className="border-t border-[var(--color-border)] align-top hover:bg-[var(--color-surface-muted)]">
                {editable ? <td className="px-3 py-3"><input type="checkbox" checked={selected.has(row.id)} onChange={() => onToggle(row.id)} /></td> : null}
                <td className="px-3 py-3 font-mono text-[12px] text-[var(--color-text-muted)]">{row.row_no}</td>
                <td className="px-3 py-3 font-mono text-[12.5px] font-semibold">{row.mark ?? "—"}</td>
                <td className="px-3 py-3 text-[12.5px]">
                  {row.description ?? "—"}
                  {row.notes.length > 0 ? <div className="mt-0.5 text-[11px] text-[var(--color-warning)]">{row.notes.join(" ")}</div> : null}
                  {row.finish_name && row.finish_name !== row.description ? <div className="text-[11px] text-[var(--color-text-muted)]">{row.finish_name}</div> : null}
                </td>
                <td className="px-3 py-3 text-[12px] text-[var(--color-text-secondary)]">{row.location_text ?? "—"}{row.level_id ? <div className="text-[11px] text-[var(--color-text-muted)]">{levelName.get(row.level_id)}</div> : null}</td>
                {isFinishSchedule ? (
                  <>
                    <td className="px-3 py-3 text-[12px] font-semibold">{row.surface ?? "—"}</td>
                    <td className="px-3 py-3 text-[12px]">{row.space_id ? spaceName.get(row.space_id) ?? "—" : <Badge tone="gold">{t("schedules.noRoom", "No room link")}</Badge>}</td>
                  </>
                ) : null}
                <td className="px-3 py-3 text-right font-mono text-[12.5px]">{row.quantity !== null ? Number(row.quantity) : "—"}{row.quantity_defaulted ? <div className="text-[10.5px] text-[var(--color-warning)]">{t("schedules.defaulted", "assumed")}</div> : null}</td>
                <td className="px-3 py-3 text-[12px]">{row.unit ?? "—"}{row.canonical_unit && row.canonical_unit !== row.unit ? <div className="text-[11px] text-[var(--color-text-muted)]">→ {fmt(Number(row.canonical_quantity), 4)} {row.canonical_unit}</div> : null}</td>
                <td className="px-3 py-3 text-right font-mono text-[12px]">{row.width_mm !== null || row.height_mm !== null ? `${row.width_mm !== null ? Number(row.width_mm) : "—"} × ${row.height_mm !== null ? Number(row.height_mm) : "—"}` : "—"}</td>
                <td className="px-3 py-3 font-mono text-[12px]">{row.work_item_code ?? <span className="text-[var(--color-warning)]">{t("schedules.needsItem", "needed")}</span>}</td>
                <td className="px-3 py-3 text-right font-mono text-[12.5px]">{row.schedule_kind === "DOOR" || row.schedule_kind === "WINDOW" ? row.matched_element_count : "—"}</td>
                <td className="px-3 py-3">
                  <Badge tone={rowTone(row.review_status)}>{row.review_status}</Badge>
                  {Number(row.confidence) < ROW_CONFIDENCE_REVIEW ? <div className="mt-1 text-[11px] text-[var(--color-warning)]">{Math.round(Number(row.confidence) * 100)}%</div> : null}
                  {row.review_status === "PENDING" && rowConfirmBlocker(row) ? <div className="mt-1 max-w-[160px] text-[11px] text-[var(--color-text-muted)]">{rowConfirmBlocker(row)}</div> : null}
                </td>
                <td className="px-3 py-3 text-right">
                  {editable ? (
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setEditingId(row.id)}>{t("common.edit", "Edit")}</Button>
                      {row.review_status !== "CONFIRMED" ? <Button variant="secondary" size="sm" disabled={update.isPending} onClick={() => decide(row, "CONFIRMED")}>{t("schedules.accept", "Accept")}</Button> : null}
                      {row.review_status !== "REJECTED" ? <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => decide(row, "REJECTED")}>{t("schedules.reject", "Reject")}</Button> : null}
                      {row.review_status !== "PENDING" ? <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => decide(row, "PENDING")}>{t("schedules.undo", "Undo")}</Button> : null}
                    </div>
                  ) : null}
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </TableShell>
  );
}

interface RowEditorProps {
  row: ScheduleRowResponse;
  cols: number;
  isFinishSchedule: boolean;
  spaces: SpaceResponse[];
  levels: LevelOption[];
  saving: boolean;
  onCancel: () => void;
  onSave: (payload: ScheduleRowUpdateRequest) => void;
}

function RowEditor({ row, cols, isFinishSchedule, spaces, levels, saving, onCancel, onSave }: RowEditorProps) {
  const { t } = useTranslation();
  const init = {
    mark: row.mark ?? "", description: row.description ?? "", location_text: row.location_text ?? "", unit: row.unit ?? "",
    quantity: row.quantity !== null ? String(Number(row.quantity)) : "", width_mm: row.width_mm !== null ? String(Number(row.width_mm)) : "",
    height_mm: row.height_mm !== null ? String(Number(row.height_mm)) : "", work_item_code: row.work_item_code ?? "",
    surface: (row.surface ?? "") as Surface | "", finish_name: row.finish_name ?? "", space_id: row.space_id ?? "", level_id: row.level_id ?? "",
  };
  const [f, setF] = useState(init);
  const set = <K extends keyof typeof init>(k: K, v: (typeof init)[K]) => setF((c) => ({ ...c, [k]: v }));
  const num = (v: string) => (v === "" ? null : Number(v));
  const badNum = (v: string, min: number, strict: boolean) => v !== "" && (Number.isNaN(Number(v)) || (strict ? Number(v) <= min : Number(v) < min));
  const invalid = badNum(f.quantity, 0, false) || badNum(f.width_mm, 0, true) || badNum(f.height_mm, 0, true);

  /** Only changed keys are sent: the backend applies exactly the keys present in the request. */
  function build(): ScheduleRowUpdateRequest {
    const p: ScheduleRowUpdateRequest = {};
    if (f.mark !== init.mark) p.mark = f.mark;
    if (f.description !== init.description) p.description = f.description;
    if (f.location_text !== init.location_text) p.location_text = f.location_text;
    if (f.unit !== init.unit) p.unit = f.unit;
    if (f.quantity !== init.quantity) p.quantity = num(f.quantity);
    if (f.width_mm !== init.width_mm) p.width_mm = num(f.width_mm);
    if (f.height_mm !== init.height_mm) p.height_mm = num(f.height_mm);
    if (f.work_item_code !== init.work_item_code) p.work_item_code = f.work_item_code.trim() || null;
    if (f.surface !== init.surface) p.surface = f.surface || null;
    if (f.finish_name !== init.finish_name) p.finish_name = f.finish_name;
    if (f.space_id !== init.space_id) p.space_id = f.space_id || null;
    if (f.level_id !== init.level_id) p.level_id = f.level_id || null;
    return p;
  }
  const dirty = Object.keys(build()).length > 0;

  return (
    <>
      <tr className="border-t border-[var(--color-border)] bg-[var(--color-warning-bg)] align-top">
        <td className="px-3 py-3" colSpan={1} />
        <td className="px-3 py-3 font-mono text-[12px]">{row.row_no}</td>
        <td className="px-3 py-3"><input className={cls} value={f.mark} maxLength={100} onChange={(e) => set("mark", e.target.value)} /></td>
        <td className="px-3 py-3 space-y-1.5">
          <input className={cls} value={f.description} maxLength={500} onChange={(e) => set("description", e.target.value)} />
          {isFinishSchedule ? <input className={cls} placeholder={t("schedules.finishName", "Finish name")} value={f.finish_name} maxLength={200} onChange={(e) => set("finish_name", e.target.value)} /> : null}
        </td>
        <td className="px-3 py-3 space-y-1.5">
          <input className={cls} value={f.location_text} maxLength={300} onChange={(e) => set("location_text", e.target.value)} />
          <select className={cls} value={f.level_id} onChange={(e) => set("level_id", e.target.value)}><option value="">{t("spaces.form.noLevel", "No level")}</option>{levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select>
        </td>

        {isFinishSchedule ? (
          <>
            <td className="px-3 py-3"><select className={cls} value={f.surface} onChange={(e) => set("surface", e.target.value as Surface | "")}><option value="">—</option>{SURFACES.map((s) => <option key={s} value={s}>{s}</option>)}</select></td>
            <td className="px-3 py-3"><select className={cls} value={f.space_id} onChange={(e) => set("space_id", e.target.value)}><option value="">{t("schedules.noRoom", "No room link")}</option>{spaces.map((s) => <option key={s.id} value={s.id}>{spaceLabel(s)}</option>)}</select></td>
          </>

        ) : null}
        <td className="px-3 py-3"><input className={`${cls} text-right`} type="number" step="any" min="0" value={f.quantity} onChange={(e) => set("quantity", e.target.value)} /></td>
        <td className="px-3 py-3"><input className={cls} value={f.unit} maxLength={20} onChange={(e) => set("unit", e.target.value)} /></td>
        <td className="px-3 py-3"><div className="flex gap-1"><input className={`${cls} text-right`} type="number" step="any" min="0" placeholder="W" value={f.width_mm} onChange={(e) => set("width_mm", e.target.value)} /><input className={`${cls} text-right`} type="number" step="any" min="0" placeholder="H" value={f.height_mm} onChange={(e) => set("height_mm", e.target.value)} /></div></td>
        <td className="px-3 py-3"><input className={cls} list="schedule-work-items" value={f.work_item_code} maxLength={50} onChange={(e) => set("work_item_code", e.target.value)} /></td>
        <td className="px-3 py-3" />
        <td className="px-3 py-3" />
        <td className="px-3 py-3">
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={onCancel} disabled={saving}>{t("common.cancel", "Cancel")}</Button>
            <Button variant="primary" size="sm" disabled={saving || invalid || !dirty} onClick={() => onSave(build())}>{saving ? t("common.saving", "Saving…") : t("common.save", "Save")}</Button>
          </div>
        </td>
      </tr>
      <tr className="hidden" aria-hidden><td colSpan={cols} /></tr>
    </>
  );
}
