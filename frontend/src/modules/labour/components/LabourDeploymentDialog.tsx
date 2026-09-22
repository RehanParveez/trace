import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateLabourDeployment, useLabourSources, useLabourWorkers } from "../hooks";
import { SUGGESTED_TRADES } from "../utils/labour.utils";
import { useTranslation } from "react-i18next";

export function LabourDeploymentDialog({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const sourcesQuery = useLabourSources();
  const [sourceId, setSourceId] = useState("");
  const workersQuery = useLabourWorkers(sourceId || undefined);
  const createDeployment = useCreateLabourDeployment(projectId);
  const { showToast } = useToast();

  const [mode, setMode] = useState<"headcount" | "worker">("headcount");
  const [workerId, setWorkerId] = useState("");
  const [trade, setTrade] = useState("");
  const [dailyRate, setDailyRate] = useState("");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  const sources = sourcesQuery.data ?? [];
  const workers = workersQuery.data ?? [];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createDeployment.mutate(
      {
        source_id: sourceId,
        worker_id: mode === "worker" ? workerId : null,
        trade: trade.trim(),
        daily_rate: Number(dailyRate),
        start_date: startDate,
      },
      {
        onSuccess: () => {onClose();
          showToast({tone: "success", title: t("labour.deployment.createdToast"),});
      },
        onError: (mutationError) => setError(
          getApiErrorMessage(mutationError, t("labour.deployment.createError"),),
        ),
      },
    );
  }

  return (
    <Modal title={t("labour.deployment.title")} description={t("labour.deployment.description")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div className="flex gap-2">
          <button type="button" onClick={() => setMode("headcount")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${mode === "headcount" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("labour.deployment.headcountCategory")}</button>
          <button type="button" onClick={() => setMode("worker")} className={`flex-1 rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${mode === "worker" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>{t("labour.deployment.namedWorker")}</button>
        </div>

        <Field label={t("labour.deployment.source")}>
          <select className={inputClass} value={sourceId} onChange={(e) => setSourceId(e.target.value)} required>
            <option value="">{t("labour.deployment.selectSource")}</option>
            {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>

        {mode === "worker" ? (
          <Field label={t("labour.deployment.worker")}>
            <select className={inputClass} value={workerId} onChange={(e) => setWorkerId(e.target.value)} required disabled={!sourceId}>
              <option value="">{t("labour.deployment.selectWorker")}</option>
              {workers.map((w) => <option key={w.id} value={w.id}>{w.name} ({w.trade})</option>)}
            </select>
          </Field>
        ) : null}

        <Field label={t("labour.deployment.trade")} hint={t("labour.deployment.tradeHint")}>
          <input list="trade-suggestions" required className={inputClass} value={trade} onChange={(e) => setTrade(e.target.value)} />
          <datalist id="trade-suggestions">{SUGGESTED_TRADES.map((t) => <option key={t} value={t} />)}</datalist>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("labour.deployment.dailyRate")}><input type="number" min="0.01" step="any" required className={inputClass} value={dailyRate} onChange={(e) => setDailyRate(e.target.value)} /></Field>
          <Field label={t("labour.deployment.startDate")}><input type="date" required className={inputClass} value={startDate} onChange={(e) => setStartDate(e.target.value)} /></Field>
        </div>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createDeployment.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createDeployment.isPending || !sourceId || !trade.trim() || !dailyRate || (mode === "worker" && !workerId)}>
            {createDeployment.isPending ? t("labour.deployment.creating") : t("labour.deployment.deploy")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}