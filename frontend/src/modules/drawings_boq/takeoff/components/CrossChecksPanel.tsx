import { useTranslation } from "react-i18next";
import { Badge, ErrorState } from "../../../organizations/components/OrganizationUi";
import type { CrossCheck, CrossChecks } from "../types/takeoff.types";
import { checkTone, pagesLine, passed, summaryLine, toLookAt } from "../utils/crossChecks";
import { floorName } from "../utils/floorSources";

interface Props {
  data: CrossChecks | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}

export function CrossChecksPanel(p: Props) {
  const { t } = useTranslation();
  if (p.loading && !p.data) return null;
  if (p.error && !p.data) return <ErrorState title={t("boq.takeoff.checks.error", "Couldn't run the checks between the readers")} onRetry={p.onRetry} />;
  if (!p.data || !p.data.checks.length) return null;
  const look = toLookAt(p.data);
  const ok = passed(p.data);
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="cross-checks" data-warnings={p.data.warnings}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.checks.title", "Do the readings agree?")}</h3>
        <Badge tone={p.data.warnings ? "red" : p.data.info ? "gold" : "green"}>{summaryLine(p.data)}</Badge>
      </div>
      {look.length ? (
        <ul className="space-y-1.5">
          {look.map((c, i) => <CheckRow key={`${c.code}-${c.floor ?? ""}-${i}`} c={c} />)}
        </ul>
      ) : (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="cross-checks-clear">
          {t("boq.takeoff.checks.clear", "Everything that could be compared agrees.")}
        </p>
      )}
      {ok.length ? (
        <details data-testid="cross-checks-passed">
          <summary className="cursor-pointer text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.checks.passed", "{{n}} checks agree", { n: ok.length })}</summary>
          <ul className="mt-1 space-y-1">
            {ok.map((c, i) => <CheckRow key={`${c.code}-${c.floor ?? ""}-${i}`} c={c} />)}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function CheckRow({ c }: { c: CrossCheck }) {
  const pages = pagesLine(c.pages);
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`cross-check-${c.code}`} data-status={c.status}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={checkTone(c.status)}>{c.status === "WARN" ? "Look at this" : c.status === "INFO" ? "Half read" : "Agrees"}</Badge>
        {c.floor ? <span className="font-semibold">{floorName(c.floor)}</span> : null}
        {pages ? <span className="text-[11.5px] text-[var(--color-text-muted)]">{pages}</span> : null}
      </div>
      <p className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">{c.message}</p>
    </li>
  );
}
