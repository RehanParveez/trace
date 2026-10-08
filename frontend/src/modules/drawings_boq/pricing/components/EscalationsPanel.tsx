import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, EmptyState, ErrorState, Field, inputClass, LoadingState, Panel, PanelHeader, TableShell, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { useAddEscalation, useDeleteEscalation, useEscalations, useRateItems } from "../hooks";
import type { RateBook, RateEscalation } from "../types/pricing.types";
import {canEscalate, effectiveEscalation, factorToPercent, formatDate, formatFactor, parsePositive, todayIso,
} from "../utils/pricing.utils";
import { FormError } from "./FormError";

export function EscalationsPanel({ book, canManage }: { book: RateBook; canManage: boolean }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const query = useEscalations(book.id);
  const items = useRateItems(book.id, {});
  const addEscalation = useAddEscalation(book.id);
  const deleteEscalation = useDeleteEscalation(book.id);
  const writable = canManage && canEscalate(book);

  const [formOpen, setFormOpen] = useState(false);
  const [scope, setScope] = useState("ALL");
  const [effectiveFrom, setEffectiveFrom] = useState(todayIso());
  const [factor, setFactor] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<RateEscalation | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const [checkDate, setCheckDate] = useState(todayIso());
  const [checkTrade, setCheckTrade] = useState("");

  const rows = useMemo(
    () => [...(query.data ?? [])].sort((a, b) => b.effective_from.localeCompare(a.effective_from) || a.trade_scope.localeCompare(b.trade_scope)),
    [query.data],
  );
  const trades = useMemo(() => {
    const set = new Set<string>();
    for (const row of items.items) if (row.trade) set.add(row.trade);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [items.items]);

  const factorValue = parsePositive(factor);
  const applied = useMemo(
    () => effectiveEscalation(query.data ?? [], checkTrade, checkDate),
    [query.data, checkTrade, checkDate],
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (factorValue === null) {
      setError(t("pricing.esc.factorInvalid", "The factor must be greater than zero, e.g. 1.05 for +5%."));
      return;
    }
    addEscalation.mutate(
      { trade_scope: scope.trim() || "ALL", effective_from: effectiveFrom, factor: factorValue, note: note.trim() || null },
      {
        onSuccess: () => {
          showToast({ tone: "success", title: t("pricing.esc.addedToast", "Escalation added") });
          setFormOpen(false);
          setFactor("");
          setNote("");
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.esc.addError", "Couldn't add this escalation."))),
      },
    );
  }

  function confirmRemove() {
    if (!removing) return;
    setRemoveError(null);
    deleteEscalation.mutate(removing.id, {
      onSuccess: () => {
        showToast({ tone: "success", title: t("pricing.esc.removedToast", "Escalation removed") });
        setRemoving(null);
      },
      onError: (e) => setRemoveError(getApiErrorMessage(e, t("pricing.esc.removeError", "Couldn't remove this escalation."))),
    });
  }

  const inputSmall =
    "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]";

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.esc.eyebrow", "ESCALATIONS")}
        title={t("pricing.esc.title", "Escalation factors")}
        description={t(
          "pricing.esc.desc",
          "Dated index factors applied to the base rate when a BOQ is priced. A factor of 1.05 means +5% on the base rate. Factors are cumulative against the base rate, not compounded row on row. A trade-specific factor wins over ALL; within one scope the latest date on or before the pricing date wins.",
        )}
        action={
          writable ? (
            <Button variant="primary" size="sm" onClick={() => setFormOpen((v) => !v)}>
              {formOpen ? t("common.close", "Close") : t("pricing.esc.add", "Add escalation")}
            </Button>
          ) : null
        }
      />

      {!writable && canManage && book.status !== "DRAFT" && book.status !== "ACTIVE" ? (
        <div className="border-b border-[var(--color-border)] px-5 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
          {t("pricing.esc.frozen", "Escalations can only be changed on a draft or active book you own.")}
        </div>
      ) : null}

      {formOpen ? (
        <form onSubmit={submit} className="space-y-4 border-b border-[var(--color-border)] p-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label={t("pricing.esc.scope", "Trade scope")} hint={t("pricing.esc.scopeHint", "ALL, or a trade name such as Steel.")}>
              <input list="pricing-esc-trades" className={inputClass} value={scope} maxLength={80} onChange={(e) => setScope(e.target.value)} />
              <datalist id="pricing-esc-trades">
                <option value="ALL" />
                {trades.map((tr) => (
                  <option key={tr} value={tr} />
                ))}
              </datalist>
            </Field>
            <Field label={t("pricing.esc.effectiveFrom", "Effective from")}>
              <input required type="date" className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
            </Field>
            <Field
              label={t("pricing.esc.factor", "Factor")}
              hint={factorValue ? factorToPercent(factorValue) : t("pricing.esc.factorHint", "e.g. 1.05")}
            >
              <input
                required
                type="number"
                min="0.0001"
                step="0.0001"
                className={inputClass}
                value={factor}
                onChange={(e) => setFactor(e.target.value)}
              />
            </Field>
          </div>
          <Field label={t("pricing.esc.note", "Note")}>
            <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("pricing.esc.notePlaceholder", "e.g. Cement price notification, July")} />
          </Field>
          <FormError message={error} />
          <div className="flex justify-end">
            <Button type="submit" variant="primary" disabled={addEscalation.isPending || !effectiveFrom || factor === ""}>
              {addEscalation.isPending ? t("common.saving", "Saving…") : t("pricing.esc.save", "Add escalation")}
            </Button>
          </div>
        </form>
      ) : null}

      {query.isLoading ? (
        <LoadingState label={t("pricing.esc.loading", "Loading escalations…")} />
      ) : query.isError ? (
        <ErrorState title={t("pricing.esc.loadError", "We couldn't load the escalations")} onRetry={() => void query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon="trend"
          title={t("pricing.esc.emptyTitle", "No escalations")}
          description={t("pricing.esc.emptyDesc", "Rates are used exactly as written (factor 1.0000).")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[640px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("pricing.esc.colFrom", "Effective from")}</th>
                <th className="px-4 py-3">{t("pricing.esc.colScope", "Trade scope")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.esc.colFactor", "Factor")}</th>
                <th className="px-4 py-3">{t("pricing.esc.colNote", "Note")}</th>
                {writable ? <th className="px-4 py-3 text-right">{t("pricing.esc.colActions", "Actions")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3 text-[12.5px]">{formatDate(row.effective_from)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={row.trade_scope === "ALL" ? "slate" : "blue"}>{row.trade_scope}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-[12.5px]">
                    {formatFactor(row.factor)} <span className="text-[var(--color-text-muted)]">({factorToPercent(row.factor)})</span>
                  </td>
                  <td className="px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">{row.note ?? "—"}</td>
                  {writable ? (
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" size="sm" onClick={() => { setRemoveError(null); setRemoving(row); }}>
                        {t("pricing.esc.remove", "Remove")}
                      </Button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {rows.length > 0 ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-4 text-[12.5px]">
          <span className="font-semibold text-[var(--color-text-secondary)]">{t("pricing.esc.check", "Check the factor on")}</span>
          <input type="date" className={inputSmall} value={checkDate} onChange={(e) => setCheckDate(e.target.value)} />
          <input
            list="pricing-esc-trades"
            className={`${inputSmall} w-40`}
            value={checkTrade}
            placeholder={t("pricing.esc.checkTrade", "Trade (optional)")}
            onChange={(e) => setCheckTrade(e.target.value)}
          />
          <span className="font-mono">
            {applied
              ? `${formatFactor(applied.factor)} (${factorToPercent(applied.factor)}) · ${applied.trade_scope} · ${formatDate(applied.effective_from)}`
              : t("pricing.esc.checkNone", "×1.0000 (no escalation applies)")}
          </span>
        </div>
      ) : null}

      {removing ? (
        <ConfirmDialog
          title={t("pricing.esc.removeTitle", "Remove this escalation?")}
          description={t("pricing.esc.removeDesc", "{{factor}} for {{scope}} from {{date}}. BOQs already priced keep the factor they used.", {
            factor: formatFactor(removing.factor), scope: removing.trade_scope, date: formatDate(removing.effective_from),
          })}
          confirmLabel={t("pricing.esc.remove", "Remove")}
          pending={deleteEscalation.isPending}
          error={removeError}
          onConfirm={confirmRemove}
          onClose={() => setRemoving(null)}
        />
      ) : null}
    </Panel>
  );
}
