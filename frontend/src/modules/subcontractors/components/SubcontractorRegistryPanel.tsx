import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal, Panel, PanelHeader, TableShell, useToast,
} from "../../organizations/components/OrganizationUi";
import { useCreateSubcontractor, useSubcontractors } from "../hooks";

export function SubcontractorRegistryPanel({ canManage }: { canManage: boolean }) {
  const subsQuery = useSubcontractors();
  const createSub = useCreateSubcontractor();
  const { showToast } = useToast();
  const [formOpen, setFormOpen] = useState(false);

  return (
    <Panel>
      <PanelHeader
        eyebrow="SUBCONTRACTOR REGISTRY"
        title="Subcontractors"
        description="Companies you subcontract trade packages to — electrical, plumbing, tiling, glazing and similar."
        action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>Add subcontractor</Button> : null}
      />
      <TableShell>
        <table className="w-full min-w-[600px] text-left">
          <thead className="bg-[var(--color-surface-muted)]">
            <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
              <th className="px-4 py-3">Name</th><th className="px-4 py-3">Trade</th><th className="px-4 py-3">Contact</th>
            </tr>
          </thead>
          <tbody>
            {(subsQuery.data ?? []).map((sub) => (
              <tr key={sub.id} className="border-t border-[var(--color-border)]">
                <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{sub.name}</td>
                <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{sub.trade_specialization}</td>
                <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{sub.contact_name ?? "—"} {sub.contact_phone ? `· ${sub.contact_phone}` : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableShell>

      {formOpen ? (
        <Modal title="Add subcontractor" onClose={() => setFormOpen(false)}>
          <SubcontractorForm onSubmit={(payload) => createSub.mutate(payload, {
            onSuccess: () => { setFormOpen(false); showToast({ tone: "success", title: "Subcontractor added" }); },
          })} isPending={createSub.isPending} />
        </Modal>
      ) : null}
    </Panel>
  );
}

function SubcontractorForm({ onSubmit, isPending }: { onSubmit: (payload: any) => void; isPending: boolean }) {
  const [name, setName] = useState("");
  const [trade, setTrade] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [ntn, setNtn] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ name: name.trim(), trade_specialization: trade.trim(), contact_name: contactName.trim() || null, contact_phone: contactPhone.trim() || null, ntn_or_cnic: ntn.trim() || null });
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Company / contractor name"><input required className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></Field>
      <Field label="Trade specialization"><input required className={inputClass} value={trade} onChange={(e) => setTrade(e.target.value)} placeholder="e.g. Electrical, Plumbing, Tiling" /></Field>
      <Field label="Contact name"><input className={inputClass} value={contactName} onChange={(e) => setContactName(e.target.value)} /></Field>
      <Field label="Contact phone"><input className={inputClass} value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} /></Field>
      <Field label="NTN / CNIC (optional)"><input className={inputClass} value={ntn} onChange={(e) => setNtn(e.target.value)} /></Field>
      <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
        <Button type="submit" variant="primary" disabled={isPending || !name.trim() || !trade.trim()}>{isPending ? "Saving…" : "Add subcontractor"}</Button>
      </div>
    </form>
  );
}