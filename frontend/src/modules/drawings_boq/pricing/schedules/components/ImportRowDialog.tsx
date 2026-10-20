import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Field, inputClass, Modal } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { FormError } from "../../components/FormError";
import { useUpdateImportRow } from "../hooks/useSchedules";
import type { ImportRow, RowUpdatePayload } from "../types/schedules.types";
import { FLAG_HELP, FLAG_LABEL, flagTone, formatRate, printedRate } from "../utils/schedules.utils";

interface Props {
  importId: string;
  row: ImportRow;
  canManage: boolean;
  onClose: () => void;
}

export function ImportRowDialog({ importId, row, canManage, onClose }: Props) {
  const { t } = useTranslation();
  const update = useUpdateImportRow(importId);
  const [description, setDescription] = useState(row.description);
  const [itemNo, setItemNo] = useState(row.item_no ?? "");
  const [unit, setUnit] = useState(row.unit_raw ?? row.unit ?? "");
  const [rate, setRate] = useState(row.rate !== null && row.rate !== undefined ? String(Number(row.rate)) : "");
  const [code, setCode] = useState(row.work_item_code ?? "");
  const [note, setNote] = useState(row.note ?? "");
  const [error, setError] = useState<string | null>(null);

  function save(extra: RowUpdatePayload = {}) {
    setError(null);
    const payload: RowUpdatePayload = { ...extra };
    if (description.trim() !== row.description) payload.description = description.trim();
    if (itemNo.trim() !== (row.item_no ?? "")) payload.item_no = itemNo.trim() || null;
    if (unit.trim() && unit.trim() !== (row.unit_raw ?? row.unit ?? "")) payload.unit = unit.trim();
    const initialRate = row.rate === null || row.rate === undefined ? "" : String(Number(row.rate));
    if (rate.trim() !== initialRate) {
      const parsed = Number(rate);
      if (rate.trim() === "" || Number.isNaN(parsed) || parsed < 0) {
        setError(t("schedules.row.badRate", "Enter the rate as a number, zero or more."));
        return;
      }
      payload.rate = parsed;
    }
    const upper = code.trim().toUpperCase();
    if (upper && upper !== (row.work_item_code ?? "")) payload.work_item_code = upper;
    if (note.trim() !== (row.note ?? "")) payload.note = note.trim() || null;
    update.mutate({ rowId: row.id, payload }, { onSuccess: onClose, onError: (e) => setError(getApiErrorMessage(e, t("schedules.row.error", "That row could not be saved."))) });
  }

  const original = row.original as { description?: string; rate?: string | null; unit?: string | null } | null;

  return (
    <Modal title={t("schedules.row.title", "Row {{n}}", { n: row.seq })} description={row.page ? t("schedules.row.page", "Page {{p}}, line {{l}}", { p: row.page, l: row.line_no ?? "?" }) : undefined} onClose={onClose} wide>
      <div className="space-y-4">
        {row.raw_line ? (
          <div>
            <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">{t("schedules.row.asRead", "As it appears in the file")}</div>
            <pre className="overflow-x-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 font-mono text-[11.5px]">{row.raw_line}</pre>
          </div>
        ) : null}

        {row.flags.length > 0 ? (
          <ul className="space-y-1.5">
            {row.flags.map((flag) => (
              <li key={flag} className="flex items-start gap-2 text-[12.5px] text-[var(--color-text-secondary)]">
                <Badge tone={flagTone(flag)}>{t(`schedules.flag.${flag}`, FLAG_LABEL[flag] ?? flag)}</Badge>
                <span>{t(`schedules.flagHelp.${flag}`, FLAG_HELP[flag] ?? "")}</span>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-[120px_1fr]">
          <Field label={t("schedules.row.itemNo", "Item no")}>
            <input className={inputClass} value={itemNo} disabled={!canManage} onChange={(e) => setItemNo(e.target.value)} />
          </Field>
          <Field label={t("schedules.row.description", "Description")}>
            <textarea className={inputClass} rows={3} value={description} disabled={!canManage} onChange={(e) => setDescription(e.target.value)} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("schedules.row.unit", "Unit")} hint={t("schedules.row.unitHint", "As written: cft, sq.ft, per 100 cft, nos…")}>
            <input className={inputClass} value={unit} disabled={!canManage} onChange={(e) => setUnit(e.target.value)} />
          </Field>
          <Field label={t("schedules.row.rate", "Rate as printed")} hint={t("schedules.row.rateHint", "For the block in the unit, e.g. 45150 per 100 cft")}>
            <input className={inputClass} inputMode="decimal" value={rate} disabled={!canManage} onChange={(e) => setRate(e.target.value)} />
          </Field>
          <Field label={t("schedules.row.perUnit", "Per one unit")}>
            <div className="rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3.5 py-2.5 text-[14px]">
              {formatRate(row.unit_rate, 2)} {row.unit ? `/ ${row.unit}` : ""}
            </div>
          </Field>
        </div>
        {row.edited && original ? (
          <div className="text-[12px] text-[var(--color-text-muted)]">
            {t("schedules.row.original", "Originally read as: {{value}}", { value: `${original.description ?? ""} · ${original.rate ?? "no rate"} ${original.unit ?? ""}`.trim() })} · {printedRate(row)}
          </div>
        ) : null}

        <Field label={t("schedules.row.code", "Work item code")} hint={t("schedules.row.codeHint", "The code in your catalog this rate is for. Leave blank to keep the row out of the book.")}>
          <input className={inputClass} value={code} disabled={!canManage} onChange={(e) => setCode(e.target.value.toUpperCase())} />
        </Field>
        {row.suggestions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {row.suggestions.map((s) => (
              <button
                key={s.code}
                type="button"
                disabled={!canManage}
                onClick={() => setCode(s.code)}
                title={s.description}
                className={`rounded-[8px] border px-2.5 py-1.5 text-left text-[12px] ${code === s.code ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}
              >
                <span className="font-mono font-semibold">{s.code}</span> · {Math.round(s.score * 100)}%{s.spec_conflict ? ` · ${t("schedules.row.sizeDiffers", "size or mix differs")}` : ""}
                <span className="block max-w-[260px] truncate text-[11px] text-[var(--color-text-muted)]">{s.description}</span>
              </button>
            ))}
          </div>
        ) : null}
        <Field label={t("schedules.row.note", "Note")}>
          <input className={inputClass} value={note} maxLength={1000} disabled={!canManage} onChange={(e) => setNote(e.target.value)} />
        </Field>

        <FormError message={error} />
        {canManage ? (
          <div className="flex flex-wrap justify-between gap-2 border-t border-[var(--color-border)] pt-4">
            <div className="flex gap-2">
              <Button variant="danger" size="sm" disabled={update.isPending} onClick={() => save({ skipped: !row.skipped })}>
                {row.skipped ? t("schedules.row.unskip", "Include again") : t("schedules.row.skip", "Leave this row out")}
              </Button>
              {row.work_item_code ? <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => save({ clear_mapping: true })}>{t("schedules.row.unmap", "Remove mapping")}</Button> : null}
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={onClose}>{t("common.cancel", "Cancel")}</Button>
              <Button variant="secondary" disabled={update.isPending} onClick={() => save({ reviewed: true })}>{t("schedules.row.confirm", "Save and mark checked")}</Button>
              <Button variant="primary" disabled={update.isPending} onClick={() => save()}>{t("common.save", "Save")}</Button>
            </div>
          </div>
        ) : (
          <div className="flex justify-end border-t border-[var(--color-border)] pt-4"><Button onClick={onClose}>{t("common.close", "Close")}</Button></div>
        )}
      </div>
    </Modal>
  );
}
