import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, inputClass, useToast } from "../../../organizations/components/OrganizationUi";
import { useAdoptQsConventions, useCompanyConventions, useSaveCompanyConventions, useSaveProjectConventions } from "../hooks/useCompanyConventions";
import type { ConventionRow } from "../types/companyConventions.types";
import { takeoffErrorMessage } from "../utils/errors";

interface Props {
  canManage: boolean;
  projectId?: string;
  canOverride?: boolean;
}

function shown(r: ConventionRow): string {
  if (r.value === null) return "";
  if (r.kind === "CHOICE") return String(r.value);
  if (r.kind === "SWITCH") return Number(r.value) >= 0.5 ? "1" : "0";
  return String(r.value);
}

function inchText(r: ConventionRow, draft: string | undefined): string | null {
  if (r.unit !== "mm") return null;
  const v = Number(draft ?? r.value);
  return Number.isFinite(v) ? `${(v / 25.4).toFixed(2).replace(/\.?0+$/, "")} in` : null;
}

const CLASS_TEXT: Record<string, string> = { PRINTED: "printed", STANDARD: "standard", JUDGEMENT: "judgement" };

export function CompanyConventionsPanel({ canManage, projectId, canOverride = false }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const q = useCompanyConventions(open, projectId);
  const save = useSaveCompanyConventions();
  const saveProject = useSaveProjectConventions(projectId);
  const [overriding, setOverriding] = useState<string | null>(null);
  const [overrideDraft, setOverrideDraft] = useState<string>("");
  const adopt = useAdoptQsConventions();
  const rows = q.data?.rows ?? [];
  const groups = useMemo(() => {
    const out: Array<[string, ConventionRow[]]> = [];
    for (const r of rows) {
      const g = out.find(([name]) => name === r.group);
      if (g) g[1].push(r); else out.push([r.group, [r]]);
    }
    return out;
  }, [rows]);
  const changed = rows.filter((r) => r.editable && draft[r.key] !== undefined && draft[r.key] !== shown(r));
  const busy = save.isPending || adopt.isPending || saveProject.isPending;

  function submit(values: Record<string, number | string | null>) {
    save.mutate({ values }, {
      onSuccess: () => { setDraft({}); showToast({ tone: "success", title: t("boq.takeoff.company.saved", "Company conventions saved. Sheets already read keep their old figures until they are read again.") }); },
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.company.saveFailed", "Could not save"), description: takeoffErrorMessage(e) }),
    });
  }

  function submitProject(key: string, value: number | string | null) {
    saveProject.mutate({ values: { [key]: value } }, {
      onSuccess: () => { setOverriding(null); setOverrideDraft(""); showToast({ tone: "success", title: t("boq.takeoff.company.projectSaved", "Saved for this project. Its next calculation uses it.") }); },
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.company.saveFailed", "Could not save"), description: takeoffErrorMessage(e) }),
    });
  }

  function saveChanged() {
    const values: Record<string, number | string | null> = {};
    for (const r of changed) values[r.key] = r.kind === "CHOICE" ? draft[r.key] : Number(draft[r.key]);
    submit(values);
  }

  return (
    <section className="border-t border-[var(--color-border)] p-3 text-[12px]" data-testid="company-conventions">
      <button type="button" className="flex w-full items-center gap-2 text-left" aria-expanded={open} onClick={() => setOpen(!open)} data-testid="company-conventions-toggle">
        <h3 className="font-semibold">{t("boq.takeoff.company.title", "Company conventions")}</h3>
        {q.data ? (q.data.assumed > 0
          ? <Badge tone="gold">{t("boq.takeoff.company.assumed", "{{n}} assumed", { n: q.data.assumed })}</Badge>
          : <Badge tone="green">{t("boq.takeoff.company.allSet", "all set")}</Badge>) : null}
        <span className="ml-auto text-[11px] text-[var(--color-text-muted)]">{open ? t("boq.takeoff.company.hide", "Hide") : t("boq.takeoff.company.show", "Show")}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-3">
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.takeoff.company.help", "Figures the drawings do not print and the reader has to assume: a footing depth, a tank slab, the steel wastage. A figure your company has not set is the software's own, shown as assumed. A sheet keeps the figures it was read with until it is read again.")}
          </p>
          {q.isLoading ? <p>{t("boq.takeoff.company.loading", "Loading…")}</p> : null}
          {q.isError ? <p className="text-[var(--color-danger)]">{takeoffErrorMessage(q.error)}</p> : null}
          {q.data && canManage && q.data.assumed > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="secondary" disabled={busy} onClick={() => adopt.mutate(undefined, { onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.company.adoptFailed", "Could not save"), description: takeoffErrorMessage(e) }) })} data-testid="company-adopt-qs">
                {t("boq.takeoff.company.adopt", "Use {{qs}}'s figures for everything not set", { qs: q.data.qs_name })}
              </Button>
              <span className="text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.company.adoptHelp", "His answers of {{on}}, as the software holds them. Nothing you set is changed.", { on: q.data.qs_answered_on })}</span>
            </div>
          ) : null}
          {groups.map(([group, list]) => (
            <div key={group}>
              <h4 className="mb-1 text-[11.5px] font-semibold text-[var(--color-text-secondary)]">{group}</h4>
              <ul className="space-y-1">
                {list.map((r) => (
                  <li key={r.key} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`convention-${r.key}`} data-origin={r.origin}>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="min-w-[10rem] flex-1 font-medium">{r.label}</span>
                      {r.editable && canManage ? (
                        r.kind === "SWITCH" ? (
                          <select className={inputClass} value={draft[r.key] ?? shown(r)} disabled={busy} onChange={(e) => setDraft({ ...draft, [r.key]: e.target.value })}>
                            <option value="1">{t("boq.takeoff.company.yes", "yes")}</option>
                            <option value="0">{t("boq.takeoff.company.no", "no")}</option>
                          </select>
                        ) : (
                          <input className={`${inputClass} w-28`} type="number" step="any" min={r.low} max={r.high} value={draft[r.key] ?? shown(r)} disabled={busy} onChange={(e) => setDraft({ ...draft, [r.key]: e.target.value })} />
                        )
                      ) : (
                        <span>{r.kind === "SWITCH" ? (Number(r.value) >= 0.5 ? t("boq.takeoff.company.yes", "yes") : t("boq.takeoff.company.no", "no")) : String(r.value)}</span>
                      )}
                      <span className="w-20 text-[11px] text-[var(--color-text-muted)]">{r.unit ?? ""}{inchText(r, draft[r.key]) ? ` · ${inchText(r, draft[r.key])}` : ""}</span>
                      {r.editable ? (
                        <Badge tone={r.origin === "COMPANY" ? "blue" : r.origin === "QS_WORKBOOK" ? "green" : "gold"}>
                          {r.origin === "COMPANY" ? t("boq.takeoff.company.originCompany", "set by you") : r.origin === "QS_WORKBOOK" ? t("boq.takeoff.company.originQs", "from the QS") : t("boq.takeoff.company.originAssumed", "assumed")}
                        </Badge>
                      ) : <Badge tone="slate">{t("boq.takeoff.company.fixed", "not set here")}</Badge>}
                      {r.editable ? <span className="text-[11px] text-[var(--color-text-muted)]" data-testid={`rule-meta-${r.key}`}>{CLASS_TEXT[r.cls] ?? r.cls}{r.version !== null ? ` · v${r.version}` : ""}{Object.keys(r.scope ?? {}).length ? ` · ${JSON.stringify(r.scope)}` : ""}</span> : null}
                      {r.editable && projectId && canOverride ? (
                        <Button size="sm" variant="ghost" disabled={busy} data-testid={`override-${r.key}`} onClick={() => { setOverriding(overriding === r.key ? null : r.key); setOverrideDraft(r.project_override ? String(r.project_override.value) : shown(r)); }}>
                          {r.project_override ? t("boq.takeoff.company.projectFigure", "This project: {{v}}", { v: String(r.project_override.value) }) : t("boq.takeoff.company.overrideProject", "Set for this project")}
                        </Button>
                      ) : null}
                      {r.editable && r.sheets_read_with_other_value > 0 ? (
                        <span className="text-[11px] text-[var(--color-text-secondary)]">{t("boq.takeoff.company.stale", "{{n}} sheets read with another figure", { n: r.sheets_read_with_other_value })}</span>
                      ) : null}
                      {r.editable && canManage && r.origin !== "CODE_DEFAULT_ASSUMED" ? (
                        <Button size="sm" variant="ghost" disabled={busy} onClick={() => submit({ [r.key]: null })}>{t("boq.takeoff.company.clear", "Clear")}</Button>
                      ) : null}
                    </div>
                    {overriding === r.key ? (
                      <div className="mt-1 flex items-center gap-2">
                        <input className={`${inputClass} w-28`} type="number" step="any" min={r.low} max={r.high} value={overrideDraft} onChange={(e) => setOverrideDraft(e.target.value)} />
                        <Button size="sm" variant="primary" disabled={busy || overrideDraft === ""} onClick={() => submitProject(r.key, r.kind === "CHOICE" ? overrideDraft : Number(overrideDraft))}>{t("boq.takeoff.company.save1", "Save")}</Button>
                        {r.project_override ? <Button size="sm" variant="ghost" disabled={busy} onClick={() => submitProject(r.key, null)}>{t("boq.takeoff.company.useCompany", "Use the company's")}</Button> : null}
                      </div>
                    ) : null}
                    {r.scoped?.length ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{r.scoped.map((s) => `${JSON.stringify(s.scope)}: ${String(s.value)} (v${s.version})`).join(" · ")}</p> : null}
                    {!r.editable && r.why_fixed ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{r.why_fixed}</p> : null}
                    {r.editable && r.evidence ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{r.evidence}</p> : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {canManage && changed.length > 0 ? (
            <div className="flex gap-2">
              <Button size="sm" variant="primary" disabled={busy} onClick={saveChanged} data-testid="company-save">{t("boq.takeoff.company.save", "Save {{n}} changes", { n: changed.length })}</Button>
              <Button size="sm" variant="ghost" disabled={busy} onClick={() => setDraft({})}>{t("boq.takeoff.company.discard", "Discard")}</Button>
            </div>
          ) : null}
          {q.data && !canManage ? <p className="text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.company.readOnly", "Only someone who manages the organization can change these.")}</p> : null}
        </div>
      ) : null}
    </section>
  );
}
