import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Field, inputClass, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { FormError } from "../../components/FormError";
import { useUploadSchedule } from "../hooks/useSchedules";
import { IMPORT_MAX_BYTES, LAYOUT_PROFILES, formatBytes, rateImportPath } from "../utils/schedules.utils";

export function ScheduleUploadDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const upload = useUploadSchedule();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState(LAYOUT_PROFILES[0].value);
  const [firstPage, setFirstPage] = useState("1");
  const [lastPage, setLastPage] = useState("");
  const [bookName, setBookName] = useState("");
  const [bookCode, setBookCode] = useState("");
  const [edition, setEdition] = useState("");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isPdf = file ? file.name.toLowerCase().endsWith(".pdf") : true;

  function choose(next: File | null) {
    setError(null);
    if (next && next.size > IMPORT_MAX_BYTES) {
      setError(t("schedules.upload.tooLarge", "The file is larger than 50 MB. Split it by chapter and upload the parts."));
      return;
    }
    setFile(next);
    if (next && !bookName) setBookName(next.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
  }

  function submit() {
    if (!file) return;
    setError(null);
    const first = Math.max(1, Number.parseInt(firstPage, 10) || 1);
    const last = lastPage.trim() ? Number.parseInt(lastPage, 10) : null;
    if (last !== null && (Number.isNaN(last) || last < first)) {
      setError(t("schedules.upload.pageRange", "The last page must be after the first page."));
      return;
    }
    upload.mutate(
      {
        file, layout_profile: profile, first_page: first, last_page: isPdf ? last : null, book_code: bookCode, book_name: bookName, edition,
        jurisdiction: "", province, city, currency: "PKR", effective_from: effectiveFrom, effective_to: "",
      },
      {
        onSuccess: (created) => {
          if (created.duplicate_of_id) {
            showToast({ tone: "info", title: t("schedules.upload.duplicate", "You uploaded this exact file before"), description: t("schedules.upload.duplicateDesc", "The earlier import is still in your list.") });
          } else {
            showToast({ tone: "success", title: t("schedules.upload.done", "Schedule uploaded"), description: t("schedules.upload.doneDesc", "It is being read. The review opens when the rows are ready.") });
          }
          onClose();
          navigate(rateImportPath(created.id));
        },
        onError: (e) => setError(getApiErrorMessage(e, t("schedules.upload.error", "The upload failed. Nothing was saved."))),
      },
    );
  }

  return (
    <Modal
      title={t("schedules.upload.title", "Upload a schedule of rates")}
      description={t(
        "schedules.upload.desc",
        "A PDF or CSV of rates from a government schedule, a QS firm or a supplier. The rows are read, checked and shown for review. Nothing is priced from it until you publish it as a rate book.",
      )}
      onClose={onClose}
      wide
    >
      <div className="space-y-4">
        <div>
          <input ref={fileRef} type="file" accept=".pdf,.csv,application/pdf,text/csv" className="block w-full text-[13px]" onChange={(e) => choose(e.target.files?.[0] ?? null)} />
          {file ? <div className="mt-1.5 text-[12px] text-[var(--color-text-muted)]">{file.name} · {formatBytes(file.size)}</div> : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("schedules.upload.profile", "Page layout")} hint={LAYOUT_PROFILES.find((p) => p.value === profile)?.hint}>
            <select className={inputClass} value={profile} onChange={(e) => setProfile(e.target.value)}>
              {LAYOUT_PROFILES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </Field>
          {isPdf ? (
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("schedules.upload.firstPage", "First page")}>
                <input className={inputClass} inputMode="numeric" value={firstPage} onChange={(e) => setFirstPage(e.target.value)} />
              </Field>
              <Field label={t("schedules.upload.lastPage", "Last page")} hint={t("schedules.upload.lastHint", "Blank = to the end")}>
                <input className={inputClass} inputMode="numeric" value={lastPage} onChange={(e) => setLastPage(e.target.value)} />
              </Field>
            </div>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("schedules.upload.bookName", "Name of the rate book")}>
            <input className={inputClass} value={bookName} maxLength={200} onChange={(e) => setBookName(e.target.value)} />
          </Field>
          <Field label={t("schedules.upload.edition", "Edition")} hint={t("schedules.upload.editionHint", "For example 2026 Q1")}>
            <input className={inputClass} value={edition} maxLength={50} onChange={(e) => setEdition(e.target.value)} />
          </Field>
          <Field label={t("schedules.upload.province", "Province")}>
            <input className={inputClass} value={province} maxLength={50} onChange={(e) => setProvince(e.target.value)} />
          </Field>
          <Field label={t("schedules.upload.city", "District / city")}>
            <input className={inputClass} value={city} maxLength={100} onChange={(e) => setCity(e.target.value)} />
          </Field>
          <Field label={t("schedules.upload.effective", "Rates valid from")}>
            <input type="date" className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field label={t("schedules.upload.code", "Book code (optional)")} hint={t("schedules.upload.codeHint", "Left blank, it is made from the province and district.")}>
            <input className={inputClass} value={bookCode} maxLength={50} onChange={(e) => setBookCode(e.target.value.toUpperCase())} />
          </Field>
        </div>

        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" disabled={!file || upload.isPending} onClick={submit}>
            {upload.isPending ? t("schedules.upload.uploading", "Uploading…") : t("schedules.upload.submit", "Upload and read")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
