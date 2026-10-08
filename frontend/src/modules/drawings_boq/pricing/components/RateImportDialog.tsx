import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Field, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { useBulkUpsertRateItems, useImportRateItemsCsv } from "../hooks";
import type { RateImportResult } from "../types/pricing.types";
import { RATE_CSV_TEMPLATE, RATE_IMPORT_MAX_BYTES, parseRateRows } from "../utils/pricing.utils";
import { FormError } from "./FormError";

type Mode = "csv" | "paste";

export function RateImportDialog({ bookId, onClose }: { bookId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const importCsv = useImportRateItemsCsv(bookId);
  const bulk = useBulkUpsertRateItems(bookId);
  const fileRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>("csv");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RateImportResult | null>(null);

  const parsed = useMemo(() => parseRateRows(text), [text]);
  const pending = importCsv.isPending || bulk.isPending;

  function chooseFile(next: File | null) {
    setError(null);
    if (next && next.size > RATE_IMPORT_MAX_BYTES) {
      setError(t("pricing.import.tooLarge", "The file is larger than 5 MB."));
      return;
    }
    setFile(next);
  }

  function downloadTemplate() {
    triggerBlobDownload(new Blob([RATE_CSV_TEMPLATE], { type: "text/csv" }), "rate-book-template.csv");
  }

  function finish(done: RateImportResult) {
    setResult(done);
    showToast({
      tone: "success",
      title: t("pricing.import.doneToast", "Rates imported"),
      description: t("pricing.import.doneDesc", "{{created}} added, {{updated}} updated.", { created: done.created, updated: done.updated }),
    });
  }

  function submit() {
    setError(null);
    if (mode === "csv") {
      if (!file) return;
      importCsv.mutate(file, {
        onSuccess: finish,
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.import.error", "The import failed. Nothing was changed."))),
      });
      return;
    }
    if (parsed.errors.length > 0 || parsed.rows.length === 0) return;
    bulk.mutate(parsed.rows, {
      onSuccess: finish,
      onError: (e) => setError(getApiErrorMessage(e, t("pricing.import.error", "The import failed. Nothing was changed."))),
    });
  }

  const tabClass = (active: boolean) =>
    `rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${
      active ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"
    }`;

  return (
    <Modal
      title={t("pricing.import.title", "Import rates")}
      description={t(
        "pricing.import.desc",
        "Rows are matched on work item code and unit: existing rates are updated, new ones are added. If any row is invalid nothing is imported.",
      )}
      onClose={onClose}
      wide
    >
      {result ? (
        <div className="space-y-4">
          <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-[13.5px]">
            {t("pricing.import.summary", "{{total}} rows processed: {{created}} added and {{updated}} updated.", {
              total: result.total, created: result.created, updated: result.updated,
            })}
          </div>
          <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
            <Button variant="primary" onClick={onClose}>{t("common.close", "Close")}</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button type="button" className={tabClass(mode === "csv")} onClick={() => setMode("csv")}>
              {t("pricing.import.tabCsv", "Upload CSV")}
            </button>
            <button type="button" className={tabClass(mode === "paste")} onClick={() => setMode("paste")}>
              {t("pricing.import.tabPaste", "Paste rows")}
            </button>
          </div>

          {mode === "csv" ? (
            <div className="space-y-3">
              <p className="text-[13px] leading-5 text-[var(--color-text-secondary)]">
                {t(
                  "pricing.import.csvHelp",
                  "UTF-8 CSV with a header row. Required columns: work_item_code, unit, rate. Optional: trade, csr_ref, description, specification. Up to 5 MB.",
                )}
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                className="block w-full text-[13px]"
                onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
              />
              <Button type="button" variant="ghost" size="sm" onClick={downloadTemplate}>
                {t("pricing.import.template", "Download a CSV template")}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <Field
                label={t("pricing.import.pasteLabel", "Rows")}
                hint={t(
                  "pricing.import.pasteHint",
                  "Paste from a spreadsheet or type comma-separated. Columns in order: work item code, unit, rate, trade, CSR reference, description.",
                )}
              >
                <textarea
                  className={`${inputClass} min-h-[160px] font-mono text-[12px]`}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={"RCC-M20\tm3\t18500\tConcrete\tCSR-4.1\nSTL-60\tkg\t285\tSteel"}
                />
              </Field>
              {text.trim() ? (
                <div className="text-[12.5px] text-[var(--color-text-secondary)]">
                  {t("pricing.import.parsed", "{{n}} rows ready.", { n: parsed.rows.length })}
                </div>
              ) : null}
              {parsed.errors.length > 0 ? (
                <ul className="space-y-1 text-[12px] text-[var(--color-danger)]">
                  {parsed.errors.slice(0, 5).map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                  {parsed.errors.length > 5 ? (
                    <li>{t("pricing.import.moreErrors", "And {{n}} more.", { n: parsed.errors.length - 5 })}</li>
                  ) : null}
                </ul>
              ) : null}
            </div>
          )}

          <FormError message={error} />

          <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
            <Button type="button" variant="ghost" onClick={onClose} disabled={pending}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={submit}
              disabled={pending || (mode === "csv" ? !file : parsed.rows.length === 0 || parsed.errors.length > 0)}
            >
              {pending ? t("pricing.import.importing", "Importing…") : t("pricing.import.run", "Import")}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
