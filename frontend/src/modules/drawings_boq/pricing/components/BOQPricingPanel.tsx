import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, ErrorState, LoadingState, Panel, PanelHeader, StatCard,
} from "../../../organizations/components/OrganizationUi";
import { formatCurrency, formatDateTime } from "../../utils/drawings-boq.utils";
import { usePricingSummary } from "../hooks";
import type { PriceVersionResult } from "../types/pricing.types";
import { formatDate, rateSourceLabel, rateSourceTone } from "../utils/pricing.utils";
import { PriceRunDialog } from "./PriceRunDialog";

interface BOQPricingPanelProps {
  projectId: string;
  versionId: string;
  canPrice: boolean;
}

const SOURCE_ORDER = ["PROJECT_OVERRIDE", "RATE_BOOK", "LIBRARY", "AI_SUGGESTED", "MANUAL", "UNSOURCED", "UNPRICED"];

export function BOQPricingPanel({ projectId, versionId, canPrice }: BOQPricingPanelProps) {
  const { t } = useTranslation();
  const query = usePricingSummary(versionId);
  const [runOpen, setRunOpen] = useState(false);
  const [lastRun, setLastRun] = useState<PriceVersionResult | null>(null);

  const summary = query.data;
  const books = summary?.pricing_meta.rate_books ?? [];
  const sources = Object.entries(summary?.by_source ?? {}).sort(
    ([a], [b]) => SOURCE_ORDER.indexOf(a) - SOURCE_ORDER.indexOf(b),
  );

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.panel.eyebrow", "PRICING")}
        title={t("pricing.panel.title", "Rates and pricing")}
        description={t(
          "pricing.panel.desc",
          "Prices every line from project overrides, rate books and the material library, and records exactly where each rate came from.",
        )}
        action={
          canPrice ? (
            <Button variant="primary" size="sm" onClick={() => setRunOpen(true)}>
              {summary?.priced_at ? t("pricing.panel.reprice", "Price again") : t("pricing.panel.price", "Price BOQ")}
            </Button>
          ) : null
        }
      />

      {query.isLoading ? (
        <LoadingState label={t("pricing.panel.loading", "Loading pricing…")} />
      ) : query.isError || !summary ? (
        <div className="p-5">
          <ErrorState title={t("pricing.panel.loadError", "We couldn't load pricing")} onRetry={() => void query.refetch()} />
        </div>
      ) : (
        <div className="space-y-5 p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard
              label={t("pricing.panel.statTotal", "Priced total")}
              value={formatCurrency(summary.total)}
              note={t("pricing.panel.statTotalNote", "{{n}} lines", { n: summary.item_count })}
              icon="budget"
              tone="blue"
            />
            <StatCard
              label={t("pricing.panel.statUnpriced", "Unpriced lines")}
              value={summary.unpriced_count}
              note={summary.unpriced_count > 0 ? t("pricing.panel.unpricedNote", "Block issuing until priced or waived") : t("pricing.panel.pricedNote", "Every line has a rate")}
              icon={summary.unpriced_count > 0 ? "alert" : "check"}
              tone={summary.unpriced_count > 0 ? "gold" : "green"}
            />
            <StatCard
              label={t("pricing.panel.statLast", "Last priced")}
              value={summary.priced_at ? formatDateTime(summary.priced_at) : t("pricing.panel.never", "Never")}
              note={summary.pricing_meta.as_of ? t("pricing.panel.asOf", "As of {{date}}", { date: formatDate(summary.pricing_meta.as_of) }) : undefined}
              icon="clock"
              tone="blue"
            />
          </div>

          {sources.length > 0 ? (
            <div>
              <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                {t("pricing.panel.bySource", "Where the rates came from")}
              </div>
              <div className="flex flex-wrap gap-2">
                {sources.map(([source, count]) => (
                  <Badge key={source} tone={source === "UNPRICED" ? "red" : source === "UNSOURCED" ? "slate" : rateSourceTone(source)}>
                    {source === "UNPRICED" || source === "UNSOURCED"
                      ? t(`pricing.source.${source}`, source === "UNPRICED" ? "Unpriced" : "No source")
                      : t(`pricing.source.${source}`, rateSourceLabel(source))}
                    {": "}
                    {count}
                  </Badge>
                ))}
              </div>
            </div>
          ) : null}

          {books.length > 0 ? (
            <div>
              <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                {t("pricing.panel.books", "Rate books used (in order)")}
              </div>
              <ol className="space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {books.map((book, index) => (
                  <li key={book.id}>
                    {index + 1}. <span className="font-mono font-semibold">{book.code}</span> v{book.immutable_version}
                    {book.edition ? ` · ${book.edition}` : ""} ·{" "}
                    {book.scope === "SYSTEM" ? t("pricing.system", "System") : t("pricing.panel.yours", "Your organisation")}
                    {book.content_hash ? <span className="ml-2 font-mono text-[11px] text-[var(--color-text-muted)]">#{book.content_hash.slice(0, 8)}</span> : null}
                  </li>
                ))}
              </ol>
            </div>
          ) : null}

          {lastRun ? (
            <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[13px]">
              <div className="mb-1 font-semibold">{t("pricing.panel.lastRun", "Pricing finished")}</div>
              <div className="text-[var(--color-text-secondary)]">
                {t(
                  "pricing.panel.lastRunBody",
                  "{{changed}} lines changed, {{unpriced}} still unpriced, {{mismatch}} with a unit that doesn't convert, {{manual}} manual rates kept, {{other}} approved or estimated lines left alone. {{issues}} open review issues.",
                  {
                    changed: lastRun.changed, unpriced: lastRun.unpriced, mismatch: lastRun.unit_mismatch,
                    manual: lastRun.skipped_manual, other: lastRun.skipped_other, issues: lastRun.open_issues,
                  },
                )}
              </div>
              {lastRun.unit_mismatch > 0 ? (
                <div className="mt-2 text-[12.5px] text-[var(--color-danger)]">
                  {t("pricing.panel.mismatchWarn", "Lines with a unit mismatch block approval until they are given a rate in a compatible unit.")}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {runOpen ? (
        <PriceRunDialog projectId={projectId} versionId={versionId} onClose={() => setRunOpen(false)} onDone={setLastRun} />
      ) : null}
    </Panel>
  );
}
