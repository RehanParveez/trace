import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, inputClass, useToast } from "../../../organizations/components/OrganizationUi";
import { useConfirmRuleDraft, useImportRuleDrafts, useRejectRuleDraft, useRuleDrafts } from "../hooks/useRuleDrafts";
import type { DraftFile, RuleDraft } from "../types/ruleDrafts.types";
import { takeoffErrorMessage } from "../utils/errors";

interface Props {
  canManage: boolean;
}

function valueText(v: unknown): string {
  const text = typeof v === "string" ? v : JSON.stringify(v);
  return text.length > 140 ? `${text.slice(0, 140)}…` : text;
}

function cellText(d: RuleDraft): string {
  return `${d.source.sheet ?? "?"}!${d.source.cell ?? "?"}`;
}

export function RuleDraftsPanel({ canManage }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const q = useRuleDrafts(true);
  const importer = useImportRuleDrafts();
  const confirm = useConfirmRuleDraft();
  const reject = useRejectRuleDraft();
  const [typed, setTyped] = useState<Record<string, string>>({});
  const drafts = q.data?.drafts ?? [];
  const busy = importer.isPending || confirm.isPending || reject.isPending;

  async function onFile(file: File | undefined) {
    if (!file) return;
    try {
      const body = JSON.parse(await file.text()) as DraftFile;
      importer.mutate(body, {
        onSuccess: () => showToast({ tone: "success", title: t("boq.takeoff.drafts.imported", "Draft rules added. None is used until you confirm it.") }),
        onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.drafts.importFailed", "Could not add the draft rules"), description: takeoffErrorMessage(e) }),
      });
    } catch {
      showToast({ tone: "error", title: t("boq.takeoff.drafts.notJson", "That is not a draft_rules.json file.") });
    }
  }

  function onConfirm(d: RuleDraft) {
    let value: unknown;
    if (d.needs.length > 0) {
      try {
        value = JSON.parse(typed[d.id] ?? JSON.stringify(d.value));
      } catch {
        showToast({ tone: "error", title: t("boq.takeoff.drafts.badValue", "The value you typed is not valid JSON.") });
        return;
      }
    }
    confirm.mutate({ id: d.id, value }, {
      onSuccess: () => showToast({ tone: "success", title: t("boq.takeoff.drafts.confirmed", "Rule confirmed. Sheets already read keep their old figures until they are read again.") }),
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.drafts.confirmFailed", "Could not confirm"), description: takeoffErrorMessage(e) }),
    });
  }

  return (
    <div className="space-y-2" data-testid="rule-drafts">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-[11.5px] font-semibold text-[var(--color-text-secondary)]">{t("boq.takeoff.drafts.title", "Draft rules from a QS workbook")}</h4>
        {drafts.length > 0 ? <Badge tone="gold">{t("boq.takeoff.drafts.count", "{{n}} draft", { n: drafts.length })}</Badge> : null}
        {canManage ? (
          <label className="ml-auto text-[11px] text-[var(--color-text-muted)]">
            {t("boq.takeoff.drafts.add", "Add a draft_rules.json file")}{" "}
            <input type="file" accept="application/json,.json" disabled={busy} data-testid="rule-drafts-file" onChange={(e) => { void onFile(e.target.files?.[0]); e.target.value = ""; }} />
          </label>
        ) : null}
      </div>
      <p className="text-[11.5px] text-[var(--color-text-secondary)]">
        {t("boq.takeoff.drafts.help", "A draft is a rule read from the formulas of a QS workbook, with the cell it came from. It is not used by any calculation until you confirm it.")}
      </p>
      {q.isLoading ? <p>{t("boq.takeoff.company.loading", "Loading…")}</p> : null}
      {q.isError ? <p className="text-[var(--color-danger)]">{takeoffErrorMessage(q.error)}</p> : null}
      {!q.isLoading && drafts.length === 0 ? <p className="text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.drafts.none", "No draft rules.")}</p> : null}
      <ul className="space-y-1">
        {drafts.map((d) => (
          <li key={d.id} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`draft-${d.id}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{d.key}</span>
              <Badge tone="gold">DRAFT</Badge>
              <span className="text-[11px] text-[var(--color-text-muted)]">{Object.keys(d.scope).length ? JSON.stringify(d.scope) : ""}</span>
              <span className="text-[11px]" title={d.source.text ?? undefined}>{cellText(d)}</span>
              {d.seed ? (
                <Badge tone={d.seed.same ? "green" : "red"}>
                  {d.seed.same ? t("boq.takeoff.drafts.sameAsSeed", "same as the software's") : t("boq.takeoff.drafts.differs", "differs from the software's: {{v}}", { v: valueText(d.seed.value) })}
                </Badge>
              ) : null}
            </div>
            <p className="mt-1 font-mono text-[11px]">{valueText(d.value)}{d.unit ? ` ${d.unit}` : ""}</p>
            {d.note ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{d.note}</p> : null}
            {d.needs.length > 0 ? (
              <div className="mt-1 space-y-1">
                <p className="text-[11px] text-[var(--color-warning)]">{t("boq.takeoff.drafts.needs", "The workbook does not state: {{what}}. Type the whole value, with those figures filled in.", { what: d.needs.join(", ") })}</p>
                <textarea className={`${inputClass} w-full font-mono text-[11px]`} rows={4} value={typed[d.id] ?? JSON.stringify(d.value, null, 1)} disabled={busy || !canManage}
                  onChange={(e) => setTyped({ ...typed, [d.id]: e.target.value })} data-testid={`draft-value-${d.id}`} />
              </div>
            ) : null}
            {!d.confirmable && d.needs.length === 0 && d.why_not ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{d.why_not}</p> : null}
            {canManage ? (
              <div className="mt-1 flex gap-2">
                <Button size="sm" variant="primary" disabled={busy || (!d.confirmable && d.needs.length === 0)} onClick={() => onConfirm(d)} data-testid={`draft-confirm-${d.id}`}>{t("boq.takeoff.drafts.confirm", "Confirm")}</Button>
                <Button size="sm" variant="ghost" disabled={busy} onClick={() => reject.mutate(d.id)}>{t("boq.takeoff.drafts.reject", "Throw away")}</Button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
