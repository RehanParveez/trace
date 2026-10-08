import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Field, inputClass, LoadingState, Modal } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { formatCurrency } from "../../utils/drawings-boq.utils";
import { useRateExplain } from "../hooks";
import type { RateResolutionTrace } from "../types/pricing.types";
import { attemptLabel, factorToPercent, formatDate, formatFactor, rateSourceLabel, rateSourceTone } from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface RateExplainDialogProps {
  itemId: string;
  itemName: string;
  onOverride?: () => void;
  onClose: () => void;
}

function TraceLines({ trace, rate }: { trace: RateResolutionTrace; rate?: string | number | null }) {
  const { t } = useTranslation();
  const rows: Array<[string, string]> = [];
  if (trace.source) rows.push([t("pricing.explain.source", "Source"), t(`pricing.source.${trace.source}`, rateSourceLabel(trace.source))]);
  if (trace.rate_book_code) {
    rows.push([t("pricing.explain.book", "Rate book"), `${trace.rate_book_code}${trace.book_version ? ` v${trace.book_version}` : ""}${trace.edition ? ` · ${trace.edition}` : ""}`]);
  }
  if (trace.csr_ref) rows.push([t("pricing.explain.csr", "CSR reference"), trace.csr_ref]);
  const base = trace.base_rate ?? trace.override_rate ?? trace.rate;
  if (base !== undefined && base !== null) rows.push([t("pricing.explain.base", "Base rate"), formatCurrency(base)]);
  if (trace.escalation_factor !== undefined && trace.escalation_factor !== null) {
    rows.push([t("pricing.explain.escalation", "Escalation"), `${formatFactor(trace.escalation_factor)} (${factorToPercent(trace.escalation_factor)})`]);
  }
  if (rate !== undefined && rate !== null) rows.push([t("pricing.explain.rate", "Rate used"), formatCurrency(rate)]);
  if (trace.unit_converted) rows.push([t("pricing.explain.converted", "Unit"), t("pricing.explain.convertedYes", "Converted from {{unit}}", { unit: trace.rate_unit ?? trace.override_unit ?? trace.library_unit ?? "—" })]);
  if (trace.reason) rows.push([t("pricing.explain.reason", "Reason"), trace.reason]);
  if (trace.matched_on) rows.push([t("pricing.explain.matched", "Matched on"), trace.matched_on]);
  if (trace.as_of) rows.push([t("pricing.explain.asOf", "As of"), formatDate(trace.as_of)]);
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-1.5 text-[12.5px]">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-[var(--color-text-muted)]">{label}</dt>
          <dd className="font-medium text-[var(--color-text-primary)]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function RateExplainDialog({ itemId, itemName, onOverride, onClose }: RateExplainDialogProps) {
  const { t } = useTranslation();
  const [asOf, setAsOf] = useState("");
  const query = useRateExplain(itemId, asOf);
  const data = query.data;

  return (
    <Modal
      title={t("pricing.explain.title", "Where this rate comes from")}
      description={itemName}
      onClose={onClose}
      wide
    >
      <div className="space-y-5">
        <Field
          label={t("pricing.explain.checkDate", "Check as of")}
          hint={t("pricing.explain.checkHint", "Leave empty to use the date the BOQ was last priced.")}
        >
          <input type="date" className={inputClass} value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </Field>

        {query.isLoading ? (
          <LoadingState label={t("pricing.explain.loading", "Tracing the rate…")} />
        ) : query.isError || !data ? (
          <FormError message={getApiErrorMessage(query.error, t("pricing.explain.error", "Couldn't trace this rate."))} />
        ) : (
          <>
            <section>
              <div className="mb-2 flex items-center gap-2">
                <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">{t("pricing.explain.current", "Current rate on the line")}</h3>
                <Badge tone={rateSourceTone(data.current_source)}>
                  {data.current_source ? t(`pricing.source.${data.current_source}`, rateSourceLabel(data.current_source)) : t("pricing.source.UNPRICED", "Unpriced")}
                </Badge>
              </div>
              <div className="mb-2 font-mono text-[15px] font-semibold">
                {data.current_unit_rate !== null ? `${formatCurrency(data.current_unit_rate)} / ${data.unit}` : "—"}
              </div>
              {data.current ? (
                <TraceLines trace={data.current} />
              ) : (
                <p className="text-[12.5px] text-[var(--color-text-secondary)]">
                  {data.current_source === "MANUAL"
                    ? t("pricing.explain.manual", "This rate was typed in by hand, so there is no pricing trace.")
                    : data.current_unit_rate === null
                      ? t("pricing.explain.noRate", "The line has no rate yet.")
                      : t("pricing.explain.noTrace", "This rate has no recorded trace.")}
                </p>
              )}
            </section>

            <section>
              <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                {t("pricing.explain.wouldBe", "If priced today")}
              </h3>
              {data.would_resolve_to ? (
                <>
                  <div className="mb-2 font-mono text-[15px] font-semibold">
                    {formatCurrency(data.would_resolve_to.unit_rate ?? null)} / {data.unit}
                  </div>
                  <TraceLines trace={data.would_resolve_to} />
                </>
              ) : (
                <p className="text-[12.5px] text-[var(--color-text-secondary)]">
                  {t("pricing.explain.nothing", "No project override, rate book or library entry gives a rate for this line.")}
                </p>
              )}
            </section>

            <section>
              <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                {t("pricing.explain.tried", "What was tried, in order")}
              </h3>
              <ol className="space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {data.attempts.map((attempt, index) => (
                  <li key={`${attempt.source}-${attempt.book_id ?? index}`}>
                    {index + 1}. {attemptLabel(attempt, t)}
                  </li>
                ))}
                {data.attempts.length === 0 ? <li>{t("pricing.explain.noAttempts", "The line has no work item code, so only the library by name could match.")}</li> : null}
              </ol>
              {data.stack.length > 0 ? (
                <p className="mt-2 text-[12px] text-[var(--color-text-muted)]">
                  {t("pricing.explain.stack", "Rate books in the stack: {{books}}", { books: data.stack.map((b) => b.code).join(", ") })}
                </p>
              ) : null}
            </section>
          </>
        )}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          {onOverride ? (
            <Button variant="secondary" onClick={onOverride}>{t("pricing.explain.override", "Override this rate")}</Button>
          ) : null}
          <Button variant="primary" onClick={onClose}>{t("common.close", "Close")}</Button>
        </div>
      </div>
    </Modal>
  );
}
