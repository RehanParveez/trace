import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import type { FactsCheck } from "../types/takeoff.types";
import { factLabel, factsLine, factTone, parseFacts, sortedResults } from "../utils/knownFacts";
import { pagesLine } from "../utils/crossChecks";

interface Props {
  result: FactsCheck | undefined;
  busy: boolean;
  failed: boolean;
  onCheck: (facts: ReturnType<typeof parseFacts>["facts"]) => void;
}

const EXAMPLE = "total door 30\ncount column C1 10 ground\nroom LOUNGE 18.5 ground\nslab ground 120.4\nschedule D1 900 2100";

export function KnownFactsPanel(p: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const parsed = parseFacts(text);
  const canRun = parsed.facts.length > 0 && parsed.errors.length === 0 && !p.busy;
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="known-facts">
      <summary className="cursor-pointer font-semibold">{t("boq.takeoff.facts.title", "Check against what the drawing prints")}</summary>
      <div className="mt-2 space-y-2">
        <p className="text-[11.5px] text-[var(--color-text-secondary)]">
          {t("boq.takeoff.facts.hint", "Type what the drawing itself says, one fact to a line. Each comes back as read as printed, read differently, or not read.")}
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder={EXAMPLE}
          className="w-full rounded-[8px] border border-[var(--color-border)] bg-transparent p-2 font-mono text-[11.5px]"
          aria-label={t("boq.takeoff.facts.input", "Facts from the drawing")}
          data-testid="known-facts-input"
        />
        {parsed.errors.length ? (
          <ul className="space-y-0.5 text-[11.5px] text-[var(--color-danger,#b42318)]" data-testid="known-facts-errors">
            {parsed.errors.map((e) => <li key={e.line}>{`Line ${e.line}: ${e.message}`}</li>)}
          </ul>
        ) : null}
        <button
          type="button"
          disabled={!canRun}
          onClick={() => p.onCheck(parsed.facts)}
          className="rounded-[8px] border border-[var(--color-border)] px-3 py-1 font-semibold disabled:opacity-50"
          data-testid="known-facts-run"
        >
          {p.busy ? t("boq.takeoff.facts.running", "Checking…") : t("boq.takeoff.facts.run", "Check these")}
        </button>
        {p.failed ? <p className="text-[11.5px] text-[var(--color-danger,#b42318)]" data-testid="known-facts-failed">{t("boq.takeoff.facts.error", "Couldn't check those facts. Nothing was changed.")}</p> : null}
        {p.result && p.result.results.length ? (
          <div className="space-y-1.5" data-testid="known-facts-results">
            <Badge tone={p.result.failed ? "red" : p.result.missing ? "gold" : "green"}>{factsLine(p.result)}</Badge>
            <ul className="space-y-1.5">
              {sortedResults(p.result.results).map((r) => (
                <li key={r.index} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`known-fact-${r.index}`} data-status={r.status}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={factTone(r.status)}>{factLabel(r.status)}</Badge>
                    <span className="font-semibold">{r.text}</span>
                    {r.pages.length ? <span className="text-[11.5px] text-[var(--color-text-muted)]">{pagesLine(r.pages)}</span> : null}
                  </div>
                  <p className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">{r.message}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </details>
  );
}
