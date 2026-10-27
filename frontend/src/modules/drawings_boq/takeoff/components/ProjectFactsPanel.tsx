import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useProjectFacts } from "../hooks/useTakeoff";
import { drawingNames, factRows } from "../utils/projectFacts";
import { SourceChip } from "./SourceChip";

interface Props {
  projectId: string | undefined;
  drawings: number;
}

export function ProjectFactsPanel(p: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const facts = useProjectFacts(p.projectId, open && p.drawings > 1);
  if (p.drawings < 2) return null;
  const names = drawingNames(facts.data);
  const rows = factRows(facts.data);
  return (
    <section className="border-b border-[var(--color-border)] px-4 py-2 text-[12px]" data-testid="project-facts">
      <button type="button" className="flex w-full items-center gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open} data-testid="project-facts-toggle">
        <span className="font-semibold">{t("boq.takeoff.projectFacts.title", "What all the PDFs of this project print")}</span>
        <span className="text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.projectFacts.count", "{{n}} PDFs read together", { n: p.drawings })}</span>
        <span className="ml-auto text-[11.5px] text-[var(--color-text-secondary)]">{open ? t("boq.takeoff.projectFacts.hide", "Hide") : t("boq.takeoff.projectFacts.show", "Show")}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-2">
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.takeoff.projectFacts.help", "A fact that one PDF does not print is taken from another PDF of the project, for example a storey height printed on the architect's sections and used on the plumbing plans. Where two PDFs print different values, the PDF being read keeps its own.")}
          </p>
          {facts.isLoading ? <p className="text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.projectFacts.loading", "Reading the project…")}</p> : null}
          {facts.isError ? <p className="text-[11.5px] text-[var(--color-danger)]" data-testid="project-facts-error">{t("boq.takeoff.projectFacts.failed", "The facts of the project could not be loaded.")}</p> : null}
          {facts.data && rows.length === 0 ? <p className="text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.projectFacts.none", "No heights, thicknesses, sections or opening sizes were found in the PDFs of this project.")}</p> : null}
          <ul className="space-y-1">
            {rows.map((r) => (
              <li key={r.key} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-[8px] border border-[var(--color-border)] px-2 py-1" data-testid={`project-fact-${r.key}`}>
                <span className="font-semibold">{r.label}</span>
                <span>{r.value}</span>
                <span className="ml-auto flex flex-wrap items-center gap-1"><SourceChip sources={r.sources} names={names} /></span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
