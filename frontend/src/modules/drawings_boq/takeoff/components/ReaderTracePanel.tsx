import { useTranslation } from "react-i18next";
import { Badge, ErrorState } from "../../../organizations/components/OrganizationUi";
import type { ReaderTrace } from "../types/takeoff.types";
import { basisLabel, basisTone, decidedByLabel, orderedRules, summaryLine, thresholdPairs } from "../utils/readerTrace";

interface Props {
  data: ReaderTrace | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}

export function ReaderTracePanel(p: Props) {
  const { t } = useTranslation();
  if (p.loading && !p.data) return null;
  if (p.error && !p.data) return <ErrorState title={t("boq.takeoff.trace.error", "Couldn't work out which rules decided what")} onRetry={p.onRetry} />;
  if (!p.data || !p.data.sheets.length) return null;
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="reader-trace">
      <summary className="cursor-pointer">
        <span className="font-semibold">{t("boq.takeoff.trace.title", "Which rules decided what")}</span>
        <span className="ml-2 text-[11.5px] text-[var(--color-text-secondary)]">{summaryLine(p.data)}</span>
      </summary>
      <div className="mt-2 space-y-2">
        {p.data.sheets.map((s) => (
          <section key={s.sheet_id} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`trace-sheet-${s.page_no}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{`Page ${s.page_no}`}</span>
              <span className="text-[11.5px] text-[var(--color-text-secondary)]">{decidedByLabel(s.scale.decided_by)}</span>
              {s.scale.gate && s.scale.gate !== "OK" ? <Badge tone="red">{s.scale.gate}</Badge> : null}
            </div>
            <ul className="mt-1.5 space-y-1">
              {orderedRules(s).map((r) => (
                <li key={r.id} data-testid={`trace-rule-${r.id}`} data-basis={r.basis}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={basisTone(r.basis)}>{basisLabel(r.basis)}</Badge>
                    <span>{r.label}</span>
                    <span className="text-[11.5px] text-[var(--color-text-muted)]">{r.items ? `${r.items} items` : ""}{r.items && r.notes ? " · " : ""}{r.notes ? `${r.notes} notes` : ""}</span>
                  </div>
                  {r.basis !== "STANDARD" && thresholdPairs(r).length ? <p className="ml-1 text-[11px] text-[var(--color-text-muted)]">{thresholdPairs(r).join(" · ")}</p> : null}
                  {r.examples.length ? <p className="ml-1 text-[11px] text-[var(--color-text-secondary)]">{r.examples.join(", ")}</p> : null}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </details>
  );
}
