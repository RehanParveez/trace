import { useState } from "react";
import type { FormEvent } from "react";
import { Button, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, TableShell, useToast } from "../../organizations/components/OrganizationUi";
import { useCreateLabourRate, useLabourRates, useUpdateLabourRate } from "../hooks";
import { getApiErrorMessage } from "../../identity";
import { formatCurrency } from "../utils/drawings-boq.utils";
import type { LabourRate } from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

interface LabourRatesPanelProps {
  canManage: boolean;
}

export function LabourRatesPanel({ canManage }: LabourRatesPanelProps) {
  const { t } = useTranslation();
  const ratesQuery = useLabourRates();
  const createRate = useCreateLabourRate();
  const updateRate = useUpdateLabourRate();

  const [formOpen, setFormOpen] = useState(false);
  const [trade, setTrade] = useState("");
  const [unit, setUnit] = useState("Sft");
  const [rate, setRate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useToast();

  const rates = ratesQuery.data ?? [];
  const cls = "mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createRate.mutate(
      { trade: trade.trim(), unit: unit.trim(), rate: Number(rate) },
      {
        onSuccess: () => {
          setTrade("");
          setUnit("Sft");
          setRate("");
          setFormOpen(false);
          showToast({
            tone: "success",
            title: t("labour.createdToast"),
          });
        },
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, t("labour.createError"))),
      },
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("labour.eyebrow")}
        title={t("labour.title")}
        description={t("labour.description")}
        action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen((v) => !v)}>{formOpen ? t("common.close") : t("labour.add")}</Button> : null}
      />

      {formOpen ? (
        <form onSubmit={submit} className="grid gap-3 border-b border-[#e1d5bc] p-5 sm:grid-cols-3">
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("labour.trade")} *</span>
            <input className={cls} required value={trade} onChange={(e) => setTrade(e.target.value)} placeholder={t("labour.tradePlaceholder")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("labour.unit")} *</span>
            <input className={cls} required value={unit} onChange={(e) => setUnit(e.target.value)} placeholder={t("labour.unitPlaceholder")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("labour.rate")} *</span>
            <input className={cls} required type="number" step="any" value={rate} onChange={(e) => setRate(e.target.value)} placeholder={t("labour.ratePlaceholder")} />
          </label>
          {error ? <div className="sm:col-span-3 rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div> : null}
          <div className="sm:col-span-3 flex justify-end">
            <Button type="submit" variant="primary" disabled={createRate.isPending}>{createRate.isPending ? t("common.saving") : t("labour.save")}</Button>
          </div>
        </form>
      ) : null}

      {ratesQuery.isLoading ? (
        <LoadingState label={t("labour.loading")} />
      ) : ratesQuery.isError ? (
        <ErrorState title={t("labour.loadError")} onRetry={() => void ratesQuery.refetch()} />
      ) : rates.length === 0 ? (
        <EmptyState icon="info" title={t("labour.emptyTitle")} description={t("labour.emptyDesc")} />
      ) : (
        <TableShell>
          <table className="w-full min-w-[420px] text-left">
            <thead className="bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-4 py-3">{t("labour.colTrade")}</th><th className="px-4 py-3">{t("labour.colUnit")}</th><th className="px-4 py-3 text-right">{t("labour.colRate")}</th>
              </tr>
            </thead>
            <tbody>
              {rates.map((r) => (
                <LabourRateRow
                  key={r.id}
                  rate={r}
                  canManage={canManage}
                  onSave={(newRate) =>
                    updateRate.mutate(
                      { rateId: r.id, payload: { rate: newRate } },
                      {
                        onSuccess: () =>
                          showToast({
                            tone: "success",
                            title: t("labour.rateUpdatedToast", { trade: r.trade }),
                          }),
                        onError: (error) =>
                          showToast({
                            tone: "error",
                            title: t("labour.rateErrorTitle"),
                            description: getApiErrorMessage(
                              error,
                              t("labour.rateErrorFallback"),
                            ),
                          }),
                      },
                    )
                  }
                />
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}

interface LabourRateRowProps {
  rate: LabourRate;
  canManage: boolean;
  onSave: (rate: number) => void;
}

function LabourRateRow({ rate, canManage, onSave }: LabourRateRowProps) {
  const [value, setValue] = useState(String(rate.rate));

  return (
    <tr className="border-t border-[#e1d5bc]">
      <td className="px-4 py-3 text-[11.5px] font-semibold text-[#191410]">{rate.trade}</td>
      <td className="px-4 py-3 text-[11px] text-[#6b6152]">{rate.unit}</td>
      <td className="px-4 py-3 text-right">
        {canManage ? (
          <input
            className="w-24 rounded-[6px] border border-[#d9ceb9] bg-white px-2 py-1 text-right text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
            type="number"
            step="any"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => { const n = Number(value); if (!Number.isNaN(n)) onSave(n); }}
          />
        ) : (
          <span className="font-mono text-[11px] text-[#191410]">{formatCurrency(rate.rate)}</span>
        )}
      </td>
    </tr>
  );
}