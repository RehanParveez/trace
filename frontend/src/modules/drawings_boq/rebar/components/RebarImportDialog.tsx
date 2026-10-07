import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Field, Icon, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useImportRebarFile, useImportRebarPdf } from "../hooks/useRebar";
import { formatFileSize } from "../../utils/drawings-boq.utils";
import { REBAR_FILE_EXTENSIONS, REBAR_FILE_MAX_BYTES } from "../utils/rebar.utils";
import type { Drawing, RebarImportDetail } from "../../types/drawings-boq.types";

interface RebarImportDialogProps {
  projectId: string;
  drawings: Drawing[];
  onClose: () => void;
  onCreated: (imp: RebarImportDetail) => void;
}

const selectCls = "w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12.5px]";

export function RebarImportDialog({ projectId, drawings, onClose, onCreated }: RebarImportDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const fromFile = useImportRebarFile(projectId);
  const fromPdf = useImportRebarPdf(projectId);
  const inputRef = useRef<HTMLInputElement>(null);
  const pdfs = drawings.filter((d) => d.is_current_revision && d.format === "PDF");
  const [mode, setMode] = useState<"file" | "pdf">("file");
  const [file, setFile] = useState<File | null>(null);
  const [drawingId, setDrawingId] = useState(pdfs[0]?.id ?? "");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const pending = fromFile.isPending || fromPdf.isPending;

  function pickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setError(null);
    if (f && !REBAR_FILE_EXTENSIONS.some((x) => f.name.toLowerCase().endsWith(x))) {
      setError(t("rebar.import.badType", "Upload a .csv, .txt or .xlsx file. For a PDF drawing use the PDF option."));
      setFile(null);
      return;
    }
    if (f && f.size > REBAR_FILE_MAX_BYTES) {
      setError(t("rebar.import.tooLarge", "The bar schedule file must be under 5 MB."));
      setFile(null);
      return;
    }
    setFile(f);
  }

  function submit() {
    setError(null);
    const handlers = {
      onSuccess: (imp: RebarImportDetail) => {
        showToast({ tone: "success", title: t("rebar.import.created", "Bar schedule imported"),
          description: t("rebar.import.rows", "{{n}} row(s) ready for review.", { n: imp.row_count }) });
        onCreated(imp);
        onClose();
      },
      onError: (e: unknown) => setError(getApiErrorMessage(e, t("rebar.import.error", "Couldn't import this bar schedule."))),
    };
    const n = notes.trim() || null;
    if (mode === "file" && file) fromFile.mutate({ file, notes: n }, handlers);
    else if (mode === "pdf" && drawingId) fromPdf.mutate({ drawingId, notes: n }, handlers);
  }

  const ready = mode === "file" ? !!file : !!drawingId;
  const modeCls = (a: boolean) =>
    `rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${a ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"}`;

  return (
    <Modal title={t("rebar.import.title", "Import bar bending schedule")}
      description={t("rebar.import.description", "Rows are reviewed and confirmed before any steel reaches the BOQ.")} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex gap-2">
          <button type="button" className={modeCls(mode === "file")} onClick={() => setMode("file")}>{t("rebar.import.modeFile", "CSV / Excel")}</button>
          <button type="button" className={modeCls(mode === "pdf")} onClick={() => setMode("pdf")}>{t("rebar.import.modePdf", "From PDF drawing")}</button>
        </div>

        {mode === "file" ? (
          <>
            <button type="button" onClick={() => inputRef.current?.click()}
              className="flex w-full flex-col items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center transition hover:border-[var(--color-trace-gold-dark)]">
              <Icon name="download" size={20} className="text-[var(--color-text-muted)]" />
              <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{file ? file.name : t("rebar.import.choose", "Choose a bar schedule file")}</span>
              <span className="text-[12px] text-[var(--color-text-muted)]">{file ? formatFileSize(file.size) : t("rebar.import.fileHint", ".csv, .txt or .xlsx, up to 5 MB")}</span>
            </button>
            <input ref={inputRef} type="file" accept={REBAR_FILE_EXTENSIONS.join(",")} onChange={pickFile} className="hidden" />
            <p className="text-[11.5px] text-[var(--color-text-muted)]">
              {t("rebar.import.headerHint", "Expected columns: Member, Bar mark, Member type, Shape, Dia, Nos, Length (mm), A (mm), B (mm), Total wt (kg). Sizes like 12, T12, Ø16 or #4 are read. Give units in the header, e.g. Length (mm).")}
            </p>
          </>
        ) : pdfs.length === 0 ? (
          <p className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-3 text-[12.5px] text-[var(--color-text-secondary)]">{t("rebar.import.noPdf", "Upload the structural PDF drawing first.")}</p>
        ) : (
          <>
            <Field label={t("rebar.import.pdf", "PDF drawing")}>
              <select className={selectCls} value={drawingId} onChange={(e) => setDrawingId(e.target.value)}>
                {pdfs.map((d) => <option key={d.id} value={d.id}>{d.original_filename}</option>)}
              </select>
            </Field>
            <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("rebar.import.pdfHint", "The schedule table is read from the PDF's text layer (no AI). Scanned PDFs can't be read. Check every row.")}</p>
          </>
        )}

        <Field label={t("rebar.import.notes", "Notes (optional)")}>
          <textarea className={`${inputClass} min-h-[64px]`} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={pending}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" onClick={submit} disabled={pending || !ready}>{pending ? t("rebar.import.working", "Importing…") : t("rebar.import.submit", "Import")}</Button>
        </div>
      </div>
    </Modal>
  );
}
