import { useState } from "react";
import type { FormEvent } from "react";
import {Badge, Button, Field, inputClass, Modal, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { useCreateLabourSource, useCreateLabourWorker, useLabourSources, useLabourWorkers } from "../hooks";

export function LabourRosterPanel({ canManage }: { canManage: boolean }) {
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
          eyebrow="LABOUR SOURCES"
          title="Sources"
          description="Contractors (thekedar) who supply labour, or your own direct workforce."
          action={canManage ? <Button variant="primary" size="sm" onClick={() => setSourceFormOpen(true)}>Add source</Button> : null}
        />
        <TableShell>
          <table className="w-full min-w-[500px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Name</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Contact</th>
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
          eyebrow="NAMED WORKERS"
          title="Workers"
          description="Individually tracked skilled or regular tradesmen. Daily-wage helpers can be recorded as headcount instead — no worker profile needed."
          action={canManage ? <Button variant="primary" size="sm" onClick={() => setWorkerFormOpen(true)} disabled={sources.length === 0}>Add worker</Button> : null}
        />
        <TableShell>
          <table className="w-full min-w-[560px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Name</th><th className="px-4 py-3">Trade</th><th className="px-4 py-3">Source</th><th className="px-4 py-3 text-right">Default rate</th>
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
          onSuccess: () => { setSourceFormOpen(false); showToast({ tone: "success", title: "Source added" }); },
        })} isPending={createSource.isPending} />
      ) : null}

      {workerFormOpen ? (
        <WorkerFormDialog sources={sources} onClose={() => setWorkerFormOpen(false)} onSubmit={(payload) => createWorker.mutate(payload, {
          onSuccess: () => { setWorkerFormOpen(false); showToast({ tone: "success", title: "Worker added" }); },
        })} isPending={createWorker.isPending} />
      ) : null}
    </div>
  );
}

function SourceFormDialog({ onClose, onSubmit, isPending }: { onClose: () => void; onSubmit: (payload: any) => void; isPending: boolean }) {
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState("CONTRACTOR");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ name: name.trim(), source_type: sourceType, contact_name: contactName.trim() || null, contact_phone: contactPhone.trim() || null });
  }

  return (
    <Modal title="Add labour source" description="A contractor who supplies labour, or your own direct workforce." onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Name"><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Ali Contractor, or Own Workforce" /></Field>
        <Field label="Type">
          <select className={inputClass} value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="CONTRACTOR">Contractor (thekedar)</option>
            <option value="DIRECT">Direct (company employed)</option>
          </select>
        </Field>
        <Field label="Contact name"><input className={inputClass} value={contactName} onChange={(e) => setContactName(e.target.value)} /></Field>
        <Field label="Contact phone"><input className={inputClass} value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={isPending || !name.trim()}>{isPending ? "Saving…" : "Add source"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function WorkerFormDialog({ sources, onClose, onSubmit, isPending }: { sources: { id: string; name: string }[]; onClose: () => void; onSubmit: (payload: any) => void; isPending: boolean }) {
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [name, setName] = useState("");
  const [trade, setTrade] = useState("");
  const [rate, setRate] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ source_id: sourceId, name: name.trim(), trade: trade.trim(), default_daily_rate: rate === "" ? null : Number(rate) });
  }

  return (
    <Modal title="Add worker" description="A named worker, tracked individually across projects." onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Source">
          <select className={inputClass} value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
            {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        <Field label="Name"><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Trade"><input required className={inputClass} value={trade} onChange={(e) => setTrade(e.target.value)} placeholder="e.g. Mason" /></Field>
        <Field label="Default daily rate (PKR)"><input type="number" min="0" className={inputClass} value={rate} onChange={(e) => setRate(e.target.value)} /></Field>
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={isPending || !name.trim() || !trade.trim() || !sourceId}>{isPending ? "Saving…" : "Add worker"}</Button>
        </div>
      </form>
    </Modal>
  );
}