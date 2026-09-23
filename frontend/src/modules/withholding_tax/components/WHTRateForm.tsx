import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateWHTRate } from "../hooks";
import type { WHTCategory } from "../types/withholding-tax.types";
import { useTranslation } from "react-i18next";

export function WHTRateForm({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const createRate = useCreateWHTRate();
  const { showToast } = useToast();
  const [category, setCategory] = useState<WHTCategory>("CONTRACTS_EXECUTION");
  const [filerRate, setFilerRate] = useState("");
  const [nonFilerRate, setNonFilerRate] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createRate.mutate(
      { category, filer_rate_percentage: Number(filerRate), non_filer_rate_percentage: Number(nonFilerRate), effective_from: effectiveFrom },
      { onSuccess: () => { onClose(); showToast({ tone: "success", title: t("wht.rateForm.savedToast") }) }, onError: (e) => setError(getApiErrorMessage(e, t("wht.rateForm.saveErrorFallback"))) },
    );
  }

  return (
    <Modal title={t("wht.rateForm.title")} description={t("wht.rateForm.description")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("wht.rateForm.category")}>
          <select className={inputClass} value={category} onChange={(e) => setCategory(e.target.value as WHTCategory)}>
            <option value="GOODS_SUPPLY">{t("wht.category.goodsSupply")}</option>
            <option value="SERVICES">{t("wht.category.services")}</option>
            <option value="CONTRACTS_EXECUTION">{t("wht.category.contractsExecution")}</option>
          </select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("wht.rateForm.filerRate")}><input type="number" step="0.01" min="0" max="100" required className={inputClass} value={filerRate} onChange={(e) => setFilerRate(e.target.value)} /></Field>
          <Field label={t("wht.rateForm.nonFilerRate")}><input type="number" step="0.01" min="0" max="100" required className={inputClass} value={nonFilerRate} onChange={(e) => setNonFilerRate(e.target.value)} /></Field>
        </div>
        <Field label={t("wht.rateForm.effectiveFrom")}><input type="date" required className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createRate.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createRate.isPending || !filerRate || !nonFilerRate}>{createRate.isPending ? t("common.saving") : t("wht.rateForm.save")}</Button>
        </div>
      </form>
    </Modal>
  );
}