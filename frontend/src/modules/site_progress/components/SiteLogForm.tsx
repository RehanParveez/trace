import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useCreateSiteLog } from "../hooks";
import { useTranslation } from "react-i18next";

interface SiteLogFormProps {
  projectId: string;
  onClose: () => void;
}

export function SiteLogForm({ projectId, onClose }: SiteLogFormProps) {
  const { t } = useTranslation();
  const createLog = useCreateSiteLog();
  const { showToast } = useToast();

  const [logDate, setLogDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [workforceCount, setWorkforceCount] = useState("");
  const [weather, setWeather] = useState("");
  const [blockers, setBlockers] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createLog.mutate(
      {
        project_id: projectId,
        log_date: logDate,
        workforce_count: workforceCount === "" ? null : Number(workforceCount),
        weather: weather.trim() || null,
        blockers: blockers.trim() || null,
        notes: notes.trim() || null,
      },
      {
        onSuccess: () => {
          onClose();
          showToast({ tone: "success", title: t("siteProgress.form.saved") });
        },
        onError: () => setError(t("siteProgress.form.saveError")),
      },
    );
  }

  return (
    <Modal title={t("siteProgress.form.title")} description={t("siteProgress.form.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("siteProgress.form.logDate")}>
            <input type="date" required className={inputClass} value={logDate} onChange={(e) => setLogDate(e.target.value)} />
          </Field>
           <Field label={t("siteProgress.form.workforce")}>
            <input type="number" min="0" className={inputClass} value={workforceCount} onChange={(e) => setWorkforceCount(e.target.value)} placeholder={t("siteProgress.form.workforcePlaceholder")} />
          </Field>
        </div>

        <Field label={t("siteProgress.form.weather")}>
          <input className={inputClass} value={weather} onChange={(e) => setWeather(e.target.value)} placeholder={t("siteProgress.form.weatherPlaceholder")} />
        </Field>

        <Field label={t("siteProgress.form.blockers")}>
          <textarea className={`${inputClass} resize-y`} rows={2} value={blockers} onChange={(e) => setBlockers(e.target.value)} placeholder={t("siteProgress.form.blockersPlaceholder")} />
        </Field>

        <Field label={t("siteProgress.form.notes")}>
          <textarea className={`${inputClass} resize-y`} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t("siteProgress.form.notesPlaceholder")} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createLog.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createLog.isPending || !logDate}>
            {createLog.isPending ? t("common.saving") : t("siteProgress.form.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}