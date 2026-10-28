import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, inputClass, useToast } from "../../../organizations/components/OrganizationUi";
import { useProjectMarks, useSetProjectMark } from "../hooks/useTakeoff";
import { basisText, categoryText, isCounted, markSource, MARK_CATEGORIES, wallText } from "../utils/marks";
import { takeoffErrorMessage } from "../utils/errors";

interface Props {
  projectId: string | undefined;
  canEdit: boolean;
}

export function ProjectMarksPanel(p: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const marks = useProjectMarks(p.projectId, open);
  const save = useSetProjectMark(p.projectId);
  const disciplines = (marks.data?.disciplines ?? []).filter((d) => d.marks.length > 0);

  function set(discipline: string, mark: string, category: string | null) {
    save.mutate({ discipline, mark, category }, {
      onSuccess: () => showToast({ tone: "success", title: t("boq.takeoff.marks.saved", "Mark saved. Sheets already read keep what they read until they are read again.") }),
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.marks.saveFailed", "Could not save the mark"), description: takeoffErrorMessage(e) }),
    });
  }

  return (
    <section className="border-b border-[var(--color-border)] px-4 py-2 text-[12px]" data-testid="project-marks">
      <button type="button" className="flex w-full items-center gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open} data-testid="project-marks-toggle">
        <span className="font-semibold">{t("boq.takeoff.marks.title", "What the marks mean on this project")}</span>
        <span className="ml-auto text-[11.5px] text-[var(--color-text-secondary)]">{open ? t("boq.takeoff.marks.hide", "Hide") : t("boq.takeoff.marks.show", "Show")}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-3">
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.takeoff.marks.help", "W1 is a window on an architectural plan and a wall section on a structural sheet. Each mark is taken from what the drawing says (a section title, a schedule, a legend, a section-cut symbol) and only then from its letters. Marks that are not a column, footing, beam, door or window are not counted.")}
          </p>
          {marks.isLoading ? <p className="text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.marks.loading", "Reading the marks…")}</p> : null}
          {marks.isError ? <p className="text-[11.5px] text-[var(--color-danger)]" data-testid="project-marks-error">{t("boq.takeoff.marks.failed", "The marks of the project could not be loaded.")}</p> : null}
          {marks.data && disciplines.length === 0 ? <p className="text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.marks.none", "No marks were found. Read the sheets of the drawing first.")}</p> : null}
          {disciplines.map((d) => (
            <div key={d.discipline} data-testid={`project-marks-${d.discipline}`}>
              <h4 className="mb-1 text-[11.5px] font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">{d.discipline}</h4>
              <ul className="space-y-1">
                {d.marks.map((m) => {
                  const wall = wallText(m);
                  const source = markSource(m);
                  return (
                    <li key={m.mark} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-[8px] border border-[var(--color-border)] px-2 py-1" data-testid={`project-mark-${d.discipline}-${m.mark}`}>
                      <span className="w-12 font-semibold">{m.mark}</span>
                      {p.canEdit ? (
                        <select className={inputClass} value={m.category} disabled={save.isPending} aria-label={`${m.mark} ${d.discipline}`} onChange={(e) => set(d.discipline, m.mark, e.target.value)}>
                          {MARK_CATEGORIES.map((c) => (<option key={c} value={c}>{categoryText(c)}</option>))}
                        </select>
                      ) : (
                        <span>{categoryText(m.category)}</span>
                      )}
                      {wall ? <span className="text-[11.5px] text-[var(--color-text-secondary)]">{wall}</span> : null}
                      <span className="ml-auto flex flex-wrap items-center gap-1">
                        <span title={m.text ?? undefined}><Badge tone={m.basis === "PERSON" ? "blue" : m.basis === "DEFAULT" ? "slate" : "green"}>{basisText(m.basis)}</Badge></span>
                        {source ? <Badge tone="slate">{source}</Badge> : null}
                        {isCounted(m.category) ? null : <Badge tone="slate">{t("boq.takeoff.marks.notCounted", "not counted")}</Badge>}
                        {m.conflict ? (
                          <span title={m.conflict.text ?? undefined} data-testid="project-mark-conflict"><Badge tone="gold">{t("boq.takeoff.marks.conflict", "Also read as {{what}}", { what: categoryText(m.conflict.category) })}</Badge></span>
                        ) : null}
                        {m.basis === "PERSON" && p.canEdit ? (
                          <Button size="sm" variant="ghost" disabled={save.isPending} onClick={() => set(d.discipline, m.mark, null)}>{t("boq.takeoff.marks.reset", "Back to the drawing")}</Button>
                        ) : null}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
