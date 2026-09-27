import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateSalesTaxRate } from "../hooks";
import type { SalesTaxAuthority } from "../types/sales-tax.types";
import { useTranslation } from "react-i18next";

export function SalesTaxRateForm({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
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
      { onSuccess: () => { onClose(); showToast({ tone: "success", title: t("salesTax.rateForm.savedToast") }); }, onError: (e) => setError(getApiErrorMessage(e, t("salesTax.rateForm.saveErrorFallback"))) },
    );
  }

  return (
    <Modal title={t("salesTax.rateForm.title")} description={t("salesTax.rateForm.description")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("salesTax.rateForm.authority")}>
          <select className={inputClass} value={authority} onChange={(e) => setAuthority(e.target.value as SalesTaxAuthority)}>
            <option value="PRA">{t("salesTax.authority.PRA")}</option>
            <option value="SRB">{t("salesTax.authority.SRB")}</option>
            <option value="KPRA">{t("salesTax.authority.KPRA")}</option>
            <option value="BRA">{t("salesTax.authority.BRA")}</option>
            <option value="ICT">{t("salesTax.authority.ICT")}</option>
          </select>
        </Field>
        <Field label={t("salesTax.rateForm.rate")}><input type="number" step="0.01" min="0" max="100" required className={inputClass} value={rate} onChange={(e) => setRate(e.target.value)} /></Field>
        <Field label={t("salesTax.rateForm.effectiveFrom")}><input type="date" required className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createRate.isPending}>{t("salesTax.rateForm.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createRate.isPending || !rate}>{createRate.isPending ? t("salesTax.rateForm.saving") : t("salesTax.rateForm.save")}</Button>
        </div>
      </form>
    </Modal>
  );
}