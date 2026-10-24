import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { useIntegrity } from "../hooks/useIntegrity";
import { STATE_TEXT, STATE_TONE, isEmpty, okChecks, pagesText, summaryLine, toLookAt } from "../utils/integrity";
import type { IntegrityCheck } from "../types/integrity.types";

interface Props {
  drawingId: string;
  version?: number;
}

const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";

function Row({ c }: { c: IntegrityCheck }) {
  const { t } = useTranslation();
  const pages = pagesText(c.pages);
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`integrity-${c.code}`} data-status={c.status}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={c.status === "WARN" ? "red" : c.status === "INFO" ? "gold" : "green"}>
          {c.status === "WARN" ? t("boq.takeoff.integrity.look", "Look at this") : c.status === "INFO" ? t("boq.takeoff.integrity.info", "For your information") : t("boq.takeoff.integrity.fine", "Fine")}
        </Badge>
        <span className="font-semibold">{t(`boq.takeoff.integrity.check.${c.code}`, c.title)}</span>
        {pages ? <span className={MUTED}>{pages}</span> : null}
      </div>
      <p className={`mt-1 ${MUTED}`}>{c.message}</p>
    </li>
  );
}

export function IntegrityPanel({ drawingId, version = 0 }: Props) {
  const { t } = useTranslation();
  const report = useIntegrity(drawingId, version);
  const data = report.data;
  if (report.isLoading || (report.isError && !data)) return null;
  if (!data || isEmpty(data)) return null;
  const look = toLookAt(data);
  const fine = okChecks(data);
  const line = summaryLine(data);
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="integrity-panel" data-status={data.status}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.integrity.title", "Can this read be relied on?")}</h3>
        <Badge tone={STATE_TONE[data.status]}>{t(`boq.takeoff.integrity.state.${data.status}`, STATE_TEXT[data.status])}</Badge>
        {line ? <span className={MUTED}>{line}</span> : null}
      </div>
      {look.length ? (
        <ul className="list-none space-y-1.5 pl-0">{look.map((c) => <Row key={c.code} c={c} />)}</ul>
      ) : (
        <p className={MUTED} data-testid="integrity-clear">{t("boq.takeoff.integrity.clear", "Every sheet is prepared and read with the current reader, the scale is known, and the accepted items are intact.")}</p>
      )}
      {fine.length ? (
        <details data-testid="integrity-fine">
          <summary className="cursor-pointer text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.integrity.fineCount", "{{n}} checks are fine", { n: fine.length })}</summary>
          <ul className="mt-1 list-none space-y-1 pl-0">{fine.map((c) => <Row key={c.code} c={c} />)}</ul>
        </details>
      ) : null}
    </section>
  );
}
