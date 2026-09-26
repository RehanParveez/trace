import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateSalesTaxRate } from "../hooks";
import type { SalesTaxAuthority } from "../types/sales-tax.types";

export function SalesTaxRateForm({ onClose }: { onClose: () => void }) {
  const createRate = useCreateSalesTaxRate();
  const { showToast } = useToast();
  const [authority, setAuthority] = useState<SalesTaxAuthority>("PRA");
  const [rate, setRate] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createRate.mutate(
      { authority, rate_percentage: Number(rate), effective_from: effectiveFrom },
      { onSuccess: () => { onClose(); showToast({ tone: "success", title: "Sales tax rate saved" }); }, onError: (e) => setError(getApiErrorMessage(e, "Couldn't save this rate.")) },
    );
  }

  return (
    <Modal title="Set sales tax rate" description="Enter your organization's current provincial sales tax on services rate — verify against the authority's latest notification. This replaces any previous active rate for the same authority. You can keep several authorities active at once if you operate in more than one province." onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Authority">
          <select className={inputClass} value={authority} onChange={(e) => setAuthority(e.target.value as SalesTaxAuthority)}>
            <option value="PRA">Punjab Revenue Authority (PRA)</option>
            <option value="SRB">Sindh Revenue Board (SRB)</option>
            <option value="KPRA">Khyber Pakhtunkhwa Revenue Authority (KPRA)</option>
            <option value="BRA">Balochistan Revenue Authority (BRA)</option>
            <option value="ICT">Islamabad Capital Territory (ICT)</option>
          </select>
        </Field>
        <Field label="Rate %"><input type="number" step="0.01" min="0" max="100" required className={inputClass} value={rate} onChange={(e) => setRate(e.target.value)} /></Field>
        <Field label="Effective from"><input type="date" required className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createRate.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createRate.isPending || !rate}>{createRate.isPending ? "Saving…" : "Save rate"}</Button>
        </div>
      </form>
    </Modal>
  );
}