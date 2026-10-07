import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, TableShell } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useUpdateRebarRow } from "../hooks/useRebar";
import { ROW_CONFIDENCE_REVIEW, rowTone } from "../../utils/drawings-boq.utils";
import { hasRoleFamily, num, REBAR_ROLES, rebarRowBlocker, SHAPE_PARAMS, shapeDims } from "../utils/rebar.utils";
import type { LevelOption, RebarRowUpdateRequest, RebarScheduleRow, RebarShape, RowDecision } from "../../types/drawings-boq.types";

interface RebarRowsTableProps {
  projectId: string;
  importId: string;
  rows: RebarScheduleRow[];
  shapes: RebarShape[];
  levels: LevelOption[];
  editable: boolean;
  selected: Set<string>;
  onToggle: (rowId: string) => void;
  onToggleAll: (checked: boolean) => void;
  onNotice: (message: string | null) => void;
}

const th = "px-3 py-3 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const cls = "w-full rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12.5px] outline-none focus:border-[var(--color-trace-gold-dark)]";
const COLS = 13;

export function RebarRowsTable({ projectId, importId, rows, shapes, levels, editable, selected, onToggle, onToggleAll, onNotice }: RebarRowsTableProps) {
  const { t } = useTranslation();
  const update = useUpdateRebarRow(projectId, importId);
  const [editingId, setEditingId] = useState<string | null>(null);
  const levelName = new Map(levels.map((l) => [l.id, l.name]));
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));

  function save(row: RebarScheduleRow, payload: RebarRowUpdateRequest, after?: () => void) {
    onNotice(null);
    update.mutate({ rowId: row.id, payload }, {
      onSuccess: () => after?.(),
      onError: (e) => onNotice(`${t("rebar.row", "Row")} ${row.row_no}: ${getApiErrorMessage(e, t("rebar.rowError", "couldn't update this row."))}`),
    });
  }
  const decide = (row: RebarScheduleRow, decision: RowDecision) => save(row, { review_status: decision });

  return (
    <TableShell>
      <table className="w-full min-w-[1240px] text-left">
        <thead className="bg-[var(--color-surface-muted)]"><tr>
          {editable ? <th className={th}><input type="checkbox" checked={allSelected} onChange={(e) => onToggleAll(e.target.checked)} /></th> : null}
          <th className={th}>#</th>
          <th className={th}>{t("rebar.colMember", "Member")}</th>
          <th className={th}>{t("rebar.colMark", "Bar mark")}</th>
          <th className={th}>{t("rebar.colRole", "Member type")}</th>
          <th className={th}>{t("rebar.colShape", "Shape")}</th>
          <th className={`${th} text-right`}>{t("rebar.colDia", "Dia mm")}</th>
          <th className={`${th} text-right`}>{t("rebar.colCount", "Nos")}</th>
          <th className={`${th} text-right`}>{t("rebar.colCut", "Cut mm")}</th>
          <th className={`${th} text-right`}>{t("rebar.colDeclared", "Sched. kg")}</th>
          <th className={th}>{t("rebar.colModel", "Model / level")}</th>
          <th className={th}>{t("rebar.colStatus", "Status")}</th>
          <th className={`${th} text-right`}>{t("rebar.colActions", "Actions")}</th>
        </tr></thead>
        <tbody>
          {rows.map((row) => {
            if (editingId === row.id)
              return <RebarRowEditor key={row.id} row={row} shapes={shapes} levels={levels} saving={update.isPending}
                onCancel={() => setEditingId(null)} onSave={(p) => save(row, p, () => setEditingId(null))} />;
            const blocker = row.review_status === "PENDING" ? rebarRowBlocker(row, shapes) : null;
            return (
              <tr key={row.id} className="border-t border-[var(--color-border)] align-top hover:bg-[var(--color-surface-muted)]">
                {editable ? <td className="px-3 py-3"><input type="checkbox" checked={selected.has(row.id)} onChange={() => onToggle(row.id)} /></td> : null}
                <td className="px-3 py-3 font-mono text-[12px] text-[var(--color-text-muted)]">{row.row_no}</td>
                <td className="px-3 py-3 text-[12.5px]">
                  {row.member_mark ?? "—"}
                  {row.review_note ? <div className="mt-0.5 max-w-[220px] text-[11px] text-[var(--color-warning)]">{row.review_note}</div> : null}
                </td>
                <td className="px-3 py-3 font-mono text-[12.5px] font-semibold">{row.mark ?? "—"}</td>
                <td className="px-3 py-3 text-[12px]">
                  {row.role ?? "—"}
                  {!row.matched_element_id && !hasRoleFamily(row.role) ? <div><Badge tone="gold">{t("rebar.noFamily", "set type")}</Badge></div> : null}
                </td>
                <td className="px-3 py-3 text-[12px]">{row.shape_code ?? "—"}<div className="font-mono text-[11px] text-[var(--color-text-muted)]">{shapeDims(row.shape_params)}</div></td>
                <td className="px-3 py-3 text-right font-mono text-[12.5px]">{row.dia_mm !== null ? Number(row.dia_mm) : "—"}{row.designation && row.designation !== String(Number(row.dia_mm)) ? <div className="text-[11px] text-[var(--color-text-muted)]">{row.designation}</div> : null}</td>
                <td className="px-3 py-3 text-right font-mono text-[12.5px]">{row.count ?? "—"}</td>
                <td className="px-3 py-3 text-right font-mono text-[12.5px]">{row.cut_len_mm !== null ? Number(row.cut_len_mm) : "—"}</td>
                <td className="px-3 py-3 text-right font-mono text-[12px]">{row.declared_total_kg !== null ? Number(row.declared_total_kg) : "—"}</td>
                <td className="px-3 py-3 text-[12px]">
                  {row.matched_element_id ? <Badge tone="blue">{t("rebar.matched", "matched")}</Badge> : <span className="text-[var(--color-text-muted)]">{t("rebar.unmatched", "not matched")}</span>}
                  {row.level_id ? <div className="text-[11px] text-[var(--color-text-muted)]">{levelName.get(row.level_id)}</div> : null}
                </td>
                <td className="px-3 py-3">
                  <Badge tone={rowTone(row.review_status)}>{row.review_status}</Badge>
                  {Number(row.confidence) < ROW_CONFIDENCE_REVIEW ? <div className="mt-1 text-[11px] text-[var(--color-warning)]">{Math.round(Number(row.confidence) * 100)}%</div> : null}
                  {blocker ? <div className="mt-1 max-w-[180px] text-[11px] text-[var(--color-text-muted)]">{blocker}</div> : null}
                </td>
                <td className="px-3 py-3 text-right">
                  {editable ? (
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setEditingId(row.id)}>{t("common.edit", "Edit")}</Button>
                      {row.review_status !== "CONFIRMED" ? <Button variant="secondary" size="sm" disabled={update.isPending || !!blocker} title={blocker ?? undefined} onClick={() => decide(row, "CONFIRMED")}>{t("rebar.accept", "Accept")}</Button> : null}
                      {row.review_status !== "REJECTED" ? <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => decide(row, "REJECTED")}>{t("rebar.reject", "Reject")}</Button> : null}
                      {row.review_status !== "PENDING" ? <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => decide(row, "PENDING")}>{t("rebar.undo", "Undo")}</Button> : null}
                    </div>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </TableShell>
  );
}

interface RebarRowEditorProps {
  row: RebarScheduleRow;
  shapes: RebarShape[];
  levels: LevelOption[];
  saving: boolean;
  onCancel: () => void;
  onSave: (payload: RebarRowUpdateRequest) => void;
}

const str = (v: unknown) => (v === null || v === undefined ? "" : String(Number(v)));

function RebarRowEditor({ row, shapes, levels, saving, onCancel, onSave }: RebarRowEditorProps) {
  const { t } = useTranslation();
  const initParams = Object.fromEntries(SHAPE_PARAMS.map((p) => [p, str(row.shape_params?.[p])])) as Record<string, string>;
  const init = {
    member_mark: row.member_mark ?? "", mark: row.mark ?? "", role: row.role ?? "", shape_code: row.shape_code ?? "",
    designation: row.designation ?? "", dia_mm: str(row.dia_mm), count: row.count === null ? "" : String(row.count),
    spacing_mm: str(row.spacing_mm), cut_len_mm: str(row.cut_len_mm), grade: row.grade ?? "", level_id: row.level_id ?? "",
  };
  const [f, setF] = useState(init);
  const [params, setParams] = useState(initParams);
  const set = <K extends keyof typeof init>(k: K, v: (typeof init)[K]) => setF((c) => ({ ...c, [k]: v }));
  const shape = shapes.find((s) => s.code === f.shape_code);
  const shapeParams = shape ? [...new Set(shape.segments)] : [];
  const bad = (v: string, strict: boolean) => v !== "" && (Number.isNaN(Number(v)) || (strict ? Number(v) <= 0 : Number(v) < 0));
  const invalid = bad(f.dia_mm, true) || bad(f.count, false) || bad(f.spacing_mm, true) || bad(f.cut_len_mm, false)
    || (f.count !== "" && !Number.isInteger(Number(f.count))) || shapeParams.some((p) => bad(params[p] ?? "", true));

  /** Only changed keys are sent: the backend applies exactly the keys present in the request. */
  function build(): RebarRowUpdateRequest {
    const p: RebarRowUpdateRequest = {};
    for (const k of ["member_mark", "mark", "role", "shape_code", "designation", "grade"] as const)
      if (f[k] !== init[k]) p[k] = f[k].trim() || null;
    if (f.dia_mm !== init.dia_mm && f.dia_mm !== "") p.dia_mm = Number(f.dia_mm);
    if (f.count !== init.count && f.count !== "") p.count = Number(f.count);
    if (f.spacing_mm !== init.spacing_mm) p.spacing_mm = num(f.spacing_mm);
    if (f.cut_len_mm !== init.cut_len_mm) p.cut_len_mm = num(f.cut_len_mm);
    if (f.level_id !== init.level_id) p.level_id = f.level_id || null;
    const changedParams = SHAPE_PARAMS.some((k) => (params[k] ?? "") !== (initParams[k] ?? ""));
    if (changedParams || (p.shape_code !== undefined && shapeParams.length > 0)) {
      p.shape_params = Object.fromEntries(shapeParams.filter((k) => params[k] !== "").map((k) => [k, Number(params[k])]));
    }
    return p;
  }
  const dirty = Object.keys(build()).length > 0;

  return (
    <tr className="border-t border-[var(--color-border)] bg-[var(--color-warning-bg)] align-top">
      <td className="px-3 py-3" colSpan={2}><span className="font-mono text-[12px]">{row.row_no}</span></td>
      <td className="px-3 py-3"><input className={cls} value={f.member_mark} maxLength={100} onChange={(e) => set("member_mark", e.target.value)} /></td>
      <td className="px-3 py-3"><input className={cls} value={f.mark} maxLength={50} onChange={(e) => set("mark", e.target.value)} /></td>
      <td className="px-3 py-3">
        <select className={cls} value={hasRoleFamily(f.role) ? REBAR_ROLES.find((r) => f.role.toUpperCase().startsWith(r)) ?? f.role : f.role} onChange={(e) => set("role", e.target.value)}>
          <option value="">{t("rebar.chooseRole", "Choose…")}</option>
          {REBAR_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          {f.role && !REBAR_ROLES.some((r) => f.role.toUpperCase().startsWith(r)) ? <option value={f.role}>{f.role}</option> : null}
        </select>
      </td>
      <td className="px-3 py-3 space-y-1.5">
        <select className={cls} value={f.shape_code} onChange={(e) => set("shape_code", e.target.value)}>
          <option value="">{t("rebar.noShape", "No shape (cut length)")}</option>
          {shapes.map((s) => <option key={s.id} value={s.code}>{s.code}</option>)}
        </select>
        {shapeParams.length > 0 ? (
          <div className="flex gap-1">
            {shapeParams.map((p) => (
              <input key={p} className={`${cls} text-right`} placeholder={p} title={`${p} (mm)`} type="number" step="any" min="0"
                value={params[p] ?? ""} onChange={(e) => setParams((c) => ({ ...c, [p]: e.target.value }))} />
            ))}
          </div>
        ) : null}
      </td>
      <td className="px-3 py-3 space-y-1.5">
        <input className={`${cls} text-right`} type="number" step="any" min="0" placeholder="mm" value={f.dia_mm} onChange={(e) => set("dia_mm", e.target.value)} />
        <input className={cls} placeholder={t("rebar.sizePlaceholder", "size e.g. #4")} value={f.designation} maxLength={20} onChange={(e) => set("designation", e.target.value)} />
      </td>
      <td className="px-3 py-3"><input className={`${cls} text-right`} type="number" step="1" min="0" value={f.count} onChange={(e) => set("count", e.target.value)} /></td>
      <td className="px-3 py-3 space-y-1.5">
        <input className={`${cls} text-right`} type="number" step="any" min="0" value={f.cut_len_mm} onChange={(e) => set("cut_len_mm", e.target.value)} />
        <input className={`${cls} text-right`} type="number" step="any" min="0" placeholder={t("rebar.spacing", "spacing")} value={f.spacing_mm} onChange={(e) => set("spacing_mm", e.target.value)} />
      </td>
      <td className="px-3 py-3"><input className={cls} placeholder={t("rebar.grade", "grade")} value={f.grade} maxLength={30} onChange={(e) => set("grade", e.target.value)} /></td>
      <td className="px-3 py-3">
        <select className={cls} value={f.level_id} onChange={(e) => set("level_id", e.target.value)}>
          <option value="">{t("spaces.form.noLevel", "No level")}</option>
          {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
      </td>
      <td className="px-3 py-3" />
      <td className="px-3 py-3" colSpan={COLS - 12}>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={saving}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" size="sm" disabled={saving || invalid || !dirty} onClick={() => onSave(build())}>{saving ? t("common.saving", "Saving…") : t("common.save", "Save")}</Button>
        </div>
      </td>
    </tr>
  );
}
