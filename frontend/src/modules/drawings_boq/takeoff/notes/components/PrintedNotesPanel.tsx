import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { useNotes } from "../hooks/useNotes";
import { FATE_TITLE, FATE_TONE, OPEN_FATES, groupByFate, isEmpty, noteTitle, pagesText, summaryLine } from "../utils/notes";

interface Props {
  drawingId: string;
  version?: number;
}

const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";

export function PrintedNotesPanel({ drawingId, version = 0 }: Props) {
  const { t } = useTranslation();
  const report = useNotes(drawingId, version);
  const data = report.data;
  if (report.isLoading || (report.isError && !data)) return null;
  if (!data || isEmpty(data)) return null;
  const line = summaryLine(data);
  const groups = groupByFate(data);
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="printed-notes" open={data.summary.look > 0}>
      <summary className="cursor-pointer">
        <span className="font-semibold">{t("boq.takeoff.notes.title", "What the printed notes did")}</span>
        {line ? <span className={`ml-2 ${MUTED}`}>{line}</span> : null}
      </summary>
      <div className="mt-2 space-y-3">
        <p className={MUTED}>{t("boq.takeoff.notes.hint", "Every note the drawing prints, and what became of it. A note is never applied over a size that is drawn; where the two differ, both are shown here.")}</p>

        {data.contradictions.length ? (
          <section className="space-y-1" data-testid="printed-notes-contradictions">
            <p className="font-semibold">{t("boq.takeoff.notes.contradictions", "Where the drawing contradicts a note")}</p>
            <ul className="list-none space-y-1 pl-0">
              {data.contradictions.map((c, i) => (
                <li key={`${c.code}-${i}`} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`printed-notes-flag-${c.code}`} data-severity={c.severity}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={c.severity === "warning" ? "red" : "gold"}>{c.severity === "warning" ? t("boq.takeoff.notes.look", "Look at this") : t("boq.takeoff.notes.note", "For your information")}</Badge>
                    <span className="font-semibold">{c.title}</span>
                    <span className={MUTED}>{pagesText(c.pages)}</span>
                  </div>
                  <p className={`mt-1 ${MUTED}`}>{c.message}</p>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {groups.map((g) => (
          <details key={g.fate} open={OPEN_FATES.includes(g.fate)} data-testid={`printed-notes-${g.fate}`}>
            <summary className="cursor-pointer">
              <Badge tone={FATE_TONE[g.fate]}>{t(`boq.takeoff.notes.fate.${g.fate}`, FATE_TITLE[g.fate])}</Badge>
              <span className={`ml-2 ${MUTED}`}>{g.rows.length}</span>
            </summary>
            <ul className="mt-1 list-none space-y-1 pl-0">
              {g.rows.map((r, i) => (
                <li key={`${r.kind}-${r.scope}-${r.value_mm}-${r.value}-${r.text}-${i}`} data-testid={`printed-notes-row-${r.kind}`}>
                  <span className="font-semibold">{noteTitle(r)}</span>
                  <span className={`ml-2 ${MUTED}`}>{[r.heading ? r.heading.toLowerCase() : "", pagesText(r.pages)].filter(Boolean).join(" · ")}</span>
                  <div className={MUTED}>{r.why}{r.param_text ? ` (${r.param_text})` : ""}</div>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </details>
  );
}
