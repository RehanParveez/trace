import { useRef, useState } from "react";
import { Button, Field, Icon, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateManualSchedule, useImportScheduleFile, useImportSchedulePdf } from "../hooks/useSpacesSchedules";
import { SCHEDULE_FILE_EXTENSIONS, SCHEDULE_FILE_MAX_BYTES, SCHEDULE_KINDS } from "../utils/drawings-boq.utils";
import { formatFileSize } from "../utils/drawings-boq.utils";
import type { Drawing } from "../types/drawings-boq.types";
import type { ScheduleImportResponse, ScheduleKind } from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

interface ScheduleImportDialogProps {
  projectId: string;
  drawings: Drawing[];
  onClose: () => void;
  onCreated: (imp: ScheduleImportResponse) => void;
}

type Mode = "file" | "pdf" | "manual";
const selectCls = "w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12.5px]";

export function ScheduleImportDialog({ projectId, drawings, onClose, onCreated }: ScheduleImportDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const fromFile = useImportScheduleFile(projectId);
  const fromPdf = useImportSchedulePdf(projectId);
  const manual = useCreateManualSchedule(projectId);
  const inputRef = useRef<HTMLInputElement>(null);

  const pdfs = drawings.filter((d) => d.is_current_revision && d.format === "PDF");
  const [mode, setMode] = useState<Mode>("file");
  const [kind, setKind] = useState<ScheduleKind>("DOOR");
  const [file, setFile] = useState<File | null>(null);
  const [drawingId, setDrawingId] = useState(pdfs[0]?.id ?? "");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const pending = fromFile.isPending || fromPdf.isPending || manual.isPending;

  function pickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setError(null);
    if (f && !SCHEDULE_FILE_EXTENSIONS.some((x) => f.name.toLowerCase().endsWith(x))) { setError(t("schedules.import.badType", "Upload a .csv, .txt or .xlsx file. For a PDF schedule use the PDF option.")); setFile(null); return; }
    if (f && f.size > SCHEDULE_FILE_MAX_BYTES) { setError(t("schedules.import.tooLarge", "The schedule file must be under 5 MB.")); setFile(null); return; }
    setFile(f);
  }

  function submit() {
    setError(null);
    const handlers = {
      onSuccess: (imp: ScheduleImportResponse) => {
        showToast({ tone: "success", title: t("schedules.import.created", "Schedule imported"), description: t("schedules.import.rows", "{{n}} row(s) ready for review.", { n: imp.row_count }) });
        onCreated(imp);
        onClose();
      },
      onError: (e: unknown) => setError(getApiErrorMessage(e, t("schedules.import.error", "Couldn't import this schedule."))),
    };

    const n = notes.trim() || null;
    if (mode === "file" && file) fromFile.mutate({ file, kind, notes: n }, handlers);
    else if (mode === "pdf" && drawingId) fromPdf.mutate({ drawing_id: drawingId, schedule_kind: kind, notes: n }, handlers);
    else if (mode === "manual") manual.mutate({ schedule_kind: kind, notes: n }, handlers);
  }

  const ready = mode === "file" ? !!file : mode === "pdf" ? !!drawingId : true;
  const modeCls = (a: boolean) =>
    `rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${a ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"}`;

  return (
    <Modal title={t("schedules.import.title", "Import schedule")} description={t("schedules.import.description", "Rows are reviewed before anything counts toward the BOQ.")} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex gap-2">
          <button type="button" className={modeCls(mode === "file")} onClick={() => setMode("file")}>{t("schedules.import.modeFile", "CSV / Excel")}</button>
          <button type="button" className={modeCls(mode === "pdf")} onClick={() => setMode("pdf")}>{t("schedules.import.modePdf", "From PDF")}</button>
          <button type="button" className={modeCls(mode === "manual")} onClick={() => setMode("manual")}>{t("schedules.import.modeManual", "Blank")}</button>
        </div>

        <Field label={t("schedules.import.kind", "Schedule type")}>
          <select className={selectCls} value={kind} onChange={(e) => setKind(e.target.value as ScheduleKind)}>{SCHEDULE_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}</select>
        </Field>

        {mode === "file" ? (
          <>
            <button type="button" onClick={() => inputRef.current?.click()} className="flex w-full flex-col items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center transition hover:border-[var(--color-trace-gold-dark)]">
              <Icon name="download" size={20} className="text-[var(--color-text-muted)]" />
              <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{file ? file.name : t("schedules.import.choose", "Choose a schedule file")}</span>
              <span className="text-[12px] text-[var(--color-text-muted)]">{file ? formatFileSize(file.size) : ".csv, .txt or .xlsx, up to 5 MB"}</span>
            </button>
            <input ref={inputRef} type="file" accept={SCHEDULE_FILE_EXTENSIONS.join(",")} onChange={pickFile} className="hidden" />
            <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("schedules.import.headerHint", "The first rows must contain headers such as mark, description, unit, quantity, size, location or surface.")}</p>
          </>
        ) : null}

        {mode === "pdf" ? (
          pdfs.length === 0 ? (
            <p className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-3 text-[12.5px] text-[var(--color-text-secondary)]">{t("schedules.import.noPdf", "Upload a PDF drawing first.")}</p>
          ) : (
            <>
              <Field label={t("schedules.import.pdf", "PDF drawing")}>
                <select className={selectCls} value={drawingId} onChange={(e) => setDrawingId(e.target.value)}>{pdfs.map((d) => <option key={d.id} value={d.id}>{d.original_filename}</option>)}</select>
              </Field>
              <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("schedules.import.aiHint", "Rows are read by AI from the PDF's text and use one AI request. Scanned PDFs without text can't be read. Always check the values.")}</p>
            </>
          )
        ) : null}

        {mode === "manual" ? <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("schedules.import.manualHint", "Creates an empty schedule. Add rows one by one on the next screen.")}</p> : null}

        <Field label={t("schedules.import.notes", "Notes (optional)")}>
          <textarea className={`${inputClass} min-h-[64px]`} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={pending}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" onClick={submit} disabled={pending || !ready}>{pending ? t("schedules.import.working", "Importing…") : t("schedules.import.submit", "Import")}</Button>
        </div>
      </div>
    </Modal>
  );
}
