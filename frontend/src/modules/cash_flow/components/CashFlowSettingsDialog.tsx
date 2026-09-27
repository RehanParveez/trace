import { useState } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useCashFlowSettings, useUpdateCashFlowSettings } from "../hooks";
import { useTranslation } from "react-i18next";

export function CashFlowSettingsDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const settingsQuery = useCashFlowSettings();
  const updateSettings = useUpdateCashFlowSettings();
  const { showToast } = useToast();
  const s = settingsQuery.data;

  const [procurementDays, setProcurementDays] = useState(String(s?.procurement_payment_days ?? 15));
  const [subcontractorDays, setSubcontractorDays] = useState(String(s?.subcontractor_payment_days ?? 30));
  const [clientDays, setClientDays] = useState(String(s?.client_collection_days ?? 30));
  const [labourLookback, setLabourLookback] = useState(String(s?.labour_lookback_days ?? 30));

  function save() {
    updateSettings.mutate(
      {
        procurement_payment_days: Number(procurementDays), subcontractor_payment_days: Number(subcontractorDays),
        client_collection_days: Number(clientDays), labour_lookback_days: Number(labourLookback),
      },
      { onSuccess: () => { onClose(); showToast({ tone: "success", title: t("cashFlow.settings.updatedToast") }); } },
    );
  }

  return (
<Modal
  title={t("cashFlow.settings.title")}
  description={t("cashFlow.settings.description")}
  onClose={onClose}
>
  <div className="space-y-4">
    <Field label={t("cashFlow.settings.procurementDays")}>
      <input type="number" min="0" className={inputClass} value={procurementDays} onChange={(e) => setProcurementDays(e.target.value)} />
    </Field>
    <Field label={t("cashFlow.settings.subcontractorDays")}>
      <input type="number" min="0" className={inputClass} value={subcontractorDays} onChange={(e) => setSubcontractorDays(e.target.value)} />
    </Field>
    <Field label={t("cashFlow.settings.clientDays")}>
      <input type="number" min="0" className={inputClass} value={clientDays} onChange={(e) => setClientDays(e.target.value)} />
    </Field>
    <Field label={t("cashFlow.settings.labourLookback")}>
      <input type="number" min="7" className={inputClass} value={labourLookback} onChange={(e) => setLabourLookback(e.target.value)} />
    </Field>
    <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
      <Button variant="ghost" onClick={onClose} disabled={updateSettings.isPending}>
        {t("common.cancel")}
      </Button>
      <Button variant="primary" onClick={save} disabled={updateSettings.isPending}>
        {updateSettings.isPending ? t("common.saving") : t("common.save")}
      </Button>
    </div>
  </div>
</Modal>
  );
}