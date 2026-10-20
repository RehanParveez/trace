import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button, Field, inputClass, LoadingState, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { FormError } from "../../components/FormError";
import { useRateBooks } from "../../hooks";
import { rateBookPath } from "../../utils/pricing.utils";
import { usePublishImport, useReadiness } from "../hooks/useSchedules";
import type { PublishPayload, RateImport } from "../types/schedules.types";

export function ImportPublishDialog({ imp, onClose }: { imp: RateImport; onClose: () => void }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const publish = usePublishImport(imp.id);
  const drafts = useRateBooks({ owner: "org", status: "DRAFT" });

  const [includeUnmapped, setIncludeUnmapped] = useState(false);
  const [target, setTarget] = useState<string>("new");
  const [name, setName] = useState(imp.book_name ?? imp.filename.replace(/\.[^.]+$/, ""));
  const [code, setCode] = useState(imp.book_code ?? "");
  const [edition, setEdition] = useState(imp.edition ?? "");
  const [effectiveFrom, setEffectiveFrom] = useState(imp.effective_from ?? "");
  const [error, setError] = useState<string | null>(null);
  const readiness = useReadiness(imp.id, includeUnmapped, true);

  function submit() {
    setError(null);
    const payload: PublishPayload = { include_unmapped: includeUnmapped };
    if (target === "new") {
      if (name.trim()) payload.name = name.trim();
      if (code.trim()) payload.code = code.trim();
      if (edition.trim()) payload.edition = edition.trim();
      if (effectiveFrom) payload.effective_from = effectiveFrom;
    } else {
      payload.existing_book_id = target;
    }
    publish.mutate(payload, {
      onSuccess: (result) => {
        showToast({
          tone: "success",
          title: t("schedules.publish.done", "Loaded into a draft rate book"),
          description: t("schedules.publish.doneDesc", "{{created}} rates added, {{updated}} updated, {{left}} rows left out. Review the draft, then publish it.", { created: result.created, updated: result.updated, left: result.left_out }),
        });
        onClose();
        navigate(rateBookPath(result.rate_book_id));
      },
      onError: (e) => setError(getApiErrorMessage(e, t("schedules.publish.error", "It could not be loaded. Nothing was changed."))),
    });
  }

  const r = readiness.data;

  return (
    <Modal
      title={t("schedules.publish.title", "Load into a rate book")}
      description={t("schedules.publish.desc", "The reviewed rows become the rates of a DRAFT rate book. You then publish the book the normal way, which freezes it.")}
      onClose={onClose}
      wide
    >
      <div className="space-y-4">
        {readiness.isLoading ? <LoadingState label={t("schedules.publish.checking", "Checking…")} /> : r ? (
          <div className="space-y-2">
            {r.blockers.map((b) => (
              <div key={b.code} className="flex items-start gap-2 rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12.5px] text-[var(--color-danger)]">
                <Badge tone="red">{t("schedules.publish.blocker", "Fix first")}</Badge><span>{b.message}</span>
              </div>
            ))}
            {r.warnings.map((w) => (
              <div key={w.code} className="flex items-start gap-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12.5px] text-[var(--color-text-secondary)]">
                <Badge tone="gold">{t("schedules.publish.warning", "Note")}</Badge><span>{w.message}</span>
              </div>
            ))}
            {r.can_publish ? (
              <div className="text-[12.5px] text-[var(--color-text-secondary)]">
                {t("schedules.publish.ready", "{{mapped}} mapped rows will be loaded; {{skipped}} rows are left out on purpose.", { mapped: r.counts.mapped ?? 0, skipped: r.counts.skipped ?? 0 })}
              </div>
            ) : null}
          </div>
        ) : null}

        <label className="flex items-start gap-2 text-[13px]">
          <input type="checkbox" className="mt-1" checked={includeUnmapped} onChange={(e) => setIncludeUnmapped(e.target.checked)} />
          <span>
            {t("schedules.publish.unmapped", "Also load rows that are not mapped to a work item")}
            <span className="block text-[12px] text-[var(--color-text-muted)]">{t("schedules.publish.unmappedHint", "They get a code made from the item number, so the whole schedule is kept. They price nothing until a BOQ line uses that code.")}</span>
          </span>
        </label>

        <Field label={t("schedules.publish.into", "Load into")}>
          <select className={inputClass} value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="new">{t("schedules.publish.newBook", "A new draft rate book")}</option>
            {drafts.books.map((b) => <option key={b.id} value={b.id}>{b.code} v{b.immutable_version} — {b.name}</option>)}
          </select>
        </Field>

        {target === "new" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("schedules.publish.name", "Name")}><input className={inputClass} value={name} maxLength={200} onChange={(e) => setName(e.target.value)} /></Field>
            <Field label={t("schedules.publish.code", "Code")} hint={t("schedules.publish.codeHint", "Blank = made from province and district")}><input className={inputClass} value={code} maxLength={50} onChange={(e) => setCode(e.target.value.toUpperCase())} /></Field>
            <Field label={t("schedules.publish.edition", "Edition")}><input className={inputClass} value={edition} maxLength={50} onChange={(e) => setEdition(e.target.value)} /></Field>
            <Field label={t("schedules.publish.from", "Valid from")}><input type="date" className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></Field>
          </div>
        ) : (
          <div className="text-[12.5px] text-[var(--color-text-secondary)]">{t("schedules.publish.existingHint", "Rates with the same work item and unit are updated; the others are added.")}</div>
        )}

        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" disabled={!r?.can_publish || publish.isPending} onClick={submit}>
            {publish.isPending ? t("schedules.publish.loading", "Loading…") : t("schedules.publish.submit", "Load into rate book")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
