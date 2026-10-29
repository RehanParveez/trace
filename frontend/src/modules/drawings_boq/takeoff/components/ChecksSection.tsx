import { useTranslation } from "react-i18next";
import type { DrawingCheck, DrawingFacts } from "../types/takeoff.types";
import { PictureReadsSection } from "./PictureReadsSection";
import { hasPictureReads } from "../utils/pictures";
import { detailRows, detailSizeText, detailState, hasChecks, readerMissing, sortedChecks, warningCount } from "../utils/check";

interface Props {
  facts: DrawingFacts | undefined;
}

function CheckRow({ c }: { c: DrawingCheck }) {
  const warn = c.severity === "warning";
  return (
    <li className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`check-${c.code}`}>
      <div className={`font-semibold ${warn ? "text-[var(--color-warning)]" : "text-[var(--color-text-primary)]"}`}>{c.title}</div>
      <div className="mt-0.5 text-[var(--color-text-muted)]">{c.message}</div>
    </li>
  );
}

export function ChecksSection({ facts }: Props) {
  const { t } = useTranslation();
  if (!hasChecks(facts) && !hasPictureReads(facts)) return null;
  const checks = sortedChecks(facts);
  const details = detailRows(facts);
  const warnings = warningCount(facts);
  return (
    <div className="space-y-1.5" data-testid="checks-section">
      <div className="font-semibold text-[var(--color-text-primary)]">
        {t("drawings.checks.title", "Checks between drawings")}
        {warnings > 0 ? <span className="ml-2 text-[var(--color-warning)]">{t("drawings.checks.warnings", { defaultValue: "{{n}} to look at", n: warnings })}</span> : null}
      </div>
      <p className="text-[11px] leading-snug text-[var(--color-text-muted)]">
        {t("drawings.checks.intro", "These compare what the drawing says in different places, for example a column detail against the square drawn on the plan. Nothing here changes a quantity by itself; each line says what was used.")}
      </p>
      {checks.length > 0 ? <ul className="list-none space-y-1 pl-0">{checks.map((c, i) => <CheckRow key={`${c.code}-${i}`} c={c} />)}</ul> : null}
      {details.length > 0 ? (
        <details data-testid="checks-details">
          <summary className="cursor-pointer text-[11px] text-[var(--color-text-muted)]">{t("drawings.checks.details", { defaultValue: "{{n}} column details found", n: details.length })}</summary>
          {readerMissing(facts) ? (
            <p className="mt-1 text-[11px] text-[var(--color-warning)]" data-testid="checks-reader-missing">
              {t("drawings.checks.readerMissing", "The sizes written beside these details could not be read on the server. Type the column sizes, or ask for the character reader to be installed.")}
            </p>
          ) : null}
          <ul className="mt-1 list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
            {details.map((d, i) => {
              const state = detailState(d);
              return (
                <li key={`${d.mark}-${d.page_no}-${i}`} data-testid={`detail-${d.mark}`}>
                  <span className="font-semibold text-[var(--color-text-primary)]">{d.mark}</span>
                  {state === "NOT_READ" ? ` · ${t("drawings.checks.notRead", "size not read")}` : ` · ${detailSizeText(d)}`}
                  {state === "PARTIAL" ? ` · ${t("drawings.checks.partial", "only one side read")}` : ""}
                  {d.read === "OCR_SQUARE" || d.read === "TEXT_SQUARE" ? ` · ${t("drawings.checks.square", "square box, one side read")}` : ""}
                  {d.page_no ? ` · ${t("drawings.checks.page", { defaultValue: "page {{p}}", p: d.page_no })}` : ""}
                </li>
              );
            })}
          </ul>
        </details>
      ) : null}
      <PictureReadsSection facts={facts} />
    </div>
  );
}
