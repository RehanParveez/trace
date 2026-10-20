import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Field, inputClass, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { FormError } from "../../components/FormError";
import { useReparseImport } from "../hooks/useSchedules";
import type { RateImport } from "../types/schedules.types";
import { LAYOUT_PROFILES } from "../utils/schedules.utils";

export function ReparseDialog({ imp, onClose }: { imp: RateImport; onClose: () => void }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const reparse = useReparseImport(imp.id);
  const [profile, setProfile] = useState(imp.layout_profile);
  const [first, setFirst] = useState(String(imp.first_page));
  const [last, setLast] = useState(imp.last_page ? String(imp.last_page) : "");
  const [error, setError] = useState<string | null>(null);
  const isPdf = imp.source_kind === "PDF";

  function submit() {
    setError(null);
    const firstPage = Math.max(1, Number.parseInt(first, 10) || 1);
    const lastPage = last.trim() ? Number.parseInt(last, 10) : null;
    if (lastPage !== null && (Number.isNaN(lastPage) || lastPage < firstPage)) {
      setError(t("schedules.reparse.range", "The last page must be after the first page."));
      return;
    }
    reparse.mutate(
      { layout_profile: profile, first_page: isPdf ? firstPage : undefined, last_page: isPdf ? lastPage : undefined },
      {
        onSuccess: () => { showToast({ tone: "info", title: t("schedules.reparse.started", "Reading the file again") }); onClose(); },
        onError: (e) => setError(getApiErrorMessage(e, t("schedules.reparse.error", "The file could not be read again."))),
      },
    );
  }

  return (
    <Modal
      title={t("schedules.reparse.title", "Read the file again")}
      description={t("schedules.reparse.desc", "Use this when the layout or the page range was wrong. All rows are replaced, so mapping and review work done on this import is lost.")}
      onClose={onClose}
    >
      <div className="space-y-4">
        <Field label={t("schedules.upload.profile", "Page layout")}>
          <select className={inputClass} value={profile} onChange={(e) => setProfile(e.target.value)}>
            {LAYOUT_PROFILES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </Field>
        {isPdf ? (
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("schedules.upload.firstPage", "First page")}><input className={inputClass} inputMode="numeric" value={first} onChange={(e) => setFirst(e.target.value)} /></Field>
            <Field label={t("schedules.upload.lastPage", "Last page")}><input className={inputClass} inputMode="numeric" value={last} onChange={(e) => setLast(e.target.value)} /></Field>
          </div>
        ) : null}
        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="danger" disabled={reparse.isPending} onClick={submit}>{t("schedules.reparse.submit", "Replace all rows")}</Button>
        </div>
      </div>
    </Modal>
  );
}
