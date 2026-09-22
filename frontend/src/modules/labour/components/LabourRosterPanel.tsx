import { useState } from "react";
import type { FormEvent } from "react";
import {Badge, Button, Field, inputClass, Modal, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { useCreateLabourSource, useCreateLabourWorker, useLabourSources, useLabourWorkers } from "../hooks";
import { useTranslation } from "react-i18next";

export function LabourRosterPanel({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const sourcesQuery = useLabourSources();
  const workersQuery = useLabourWorkers();
  const createSource = useCreateLabourSource();
  const createWorker = useCreateLabourWorker();
  const { showToast } = useToast();

  const [sourceFormOpen, setSourceFormOpen] = useState(false);
  const [workerFormOpen, setWorkerFormOpen] = useState(false);

  const sources = sourcesQuery.data ?? [];
  const workers = workersQuery.data ?? [];
  const sourceNameById = new Map(sources.map((s) => [s.id, s.name]));

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          eyebrow={t("labour.roster.sourcesEyebrow")}
          title={t("labour.roster.sourcesTitle")}
          description={t("labour.roster.sourcesDescription")}
          action={canManage ? <Button variant="primary" size="sm" onClick={() => setSourceFormOpen(true)}> {t("labour.roster.addSource")}</Button> : null}
        />
        <TableShell>
          <table className="w-full min-w-[500px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("labour.roster.name")}</th><th className="px-4 py-3">{t("labour.roster.type")}</th><th className="px-4 py-3">{t("labour.roster.contact")}</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{source.name}</td>
                  <td className="px-4 py-3.5"><Badge tone={source.source_type === "DIRECT" ? "blue" : "gold"}>{source.source_type}</Badge></td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{source.contact_name ?? "—"} {source.contact_phone ? `· ${source.contact_phone}` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      </Panel>

      <Panel>
        <PanelHeader
          eyebrow={t("labour.roster.workersEyebrow")}
          title={t("labour.roster.workersTitle")}
          description={t("labour.roster.workersDescription")}
          action={canManage ? <Button variant="primary" size="sm" onClick={() => setWorkerFormOpen(true)} disabled={sources.length === 0}>{t("labour.roster.addWorker")}</Button> : null}
        />
        <TableShell>
          <table className="w-full min-w-[560px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("labour.roster.name")}</th><th className="px-4 py-3">{t("labour.roster.trade")}</th><th className="px-4 py-3">{t("labour.roster.source")}</th><th className="px-4 py-3 text-right">{t("labour.roster.defaultRate")}</th>
              </tr>
            </thead>
            <tbody>
              {workers.map((worker) => (
                <tr key={worker.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{worker.name}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{worker.trade}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{sourceNameById.get(worker.source_id) ?? "—"}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px] text-[var(--color-text-primary)]">{worker.default_daily_rate ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      </Panel>

      {sourceFormOpen ? (
        <SourceFormDialog onClose={() => setSourceFormOpen(false)} onSubmit={(payload) => createSource.mutate(payload, {
          onSuccess: () => { setSourceFormOpen(false); showToast({ tone: "success", title: t("labour.roster.sourceAdded"), }); },
        })} isPending={createSource.isPending} />
      ) : null}

      {workerFormOpen ? (
        <WorkerFormDialog sources={sources} onClose={() => setWorkerFormOpen(false)} onSubmit={(payload) => createWorker.mutate(payload, {
          onSuccess: () => { setWorkerFormOpen(false); showToast({ tone: "success", title: t("labour.roster.workerAdded"), }); },
        })} isPending={createWorker.isPending} />
      ) : null}
    </div>
  );
}

function SourceFormDialog({ onClose, onSubmit, isPending }: { onClose: () => void; onSubmit: (payload: any) => void; isPending: boolean }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState("CONTRACTOR");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ name: name.trim(), source_type: sourceType, contact_name: contactName.trim() || null, contact_phone: contactPhone.trim() || null });
  }

  return (
    <Modal title={t("labour.roster.addSourceTitle")} description={t("labour.roster.addSourceDescription")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("labour.roster.name")}><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Ali Contractor, or Own Workforce" /></Field>
        <Field label={t("labour.roster.type")}>
          <select className={inputClass} value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="CONTRACTOR">{t("labour.roster.contractor")}</option>
            <option value="DIRECT">{t("labour.roster.direct")}</option>
          </select>
        </Field>
        <Field label={t("labour.roster.contactName")}><input className={inputClass} value={contactName} onChange={(e) => setContactName(e.target.value)} /></Field>
        <Field label={t("labour.roster.contactPhone")}><input className={inputClass} value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={isPending || !name.trim()}>{isPending ? t("common.saving") : t("labour.roster.addSource")}</Button>
        </div>
      </form>
    </Modal>
  );
}

function WorkerFormDialog({ sources, onClose, onSubmit, isPending }: { sources: { id: string; name: string }[]; onClose: () => void; onSubmit: (payload: any) => void; isPending: boolean }) {
  const { t } = useTranslation();
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [name, setName] = useState("");
  const [trade, setTrade] = useState("");
  const [rate, setRate] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ source_id: sourceId, name: name.trim(), trade: trade.trim(), default_daily_rate: rate === "" ? null : Number(rate) });
  }

  return (
    <Modal title={t("labour.roster.addWorkerTitle")} description={t("labour.roster.addWorkerDescription")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("labour.roster.source")}>
          <select className={inputClass} value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
            {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        <Field label={t("labour.roster.name")}><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label={t("labour.roster.trade")}><input required className={inputClass} value={trade} onChange={(e) => setTrade(e.target.value)} placeholder={t("labour.roster.tradePlaceholder")} /></Field>
        <Field label={t("labour.roster.defaultDailyRate")}><input type="number" min="0" className={inputClass} value={rate} onChange={(e) => setRate(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={isPending || !name.trim() || !trade.trim() || !sourceId}>{isPending ? t("common.saving") : t("labour.roster.addWorker")}</Button>
        </div>
      </form>
    </Modal>
  );
}