import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useAddCustomBOQItem } from "../hooks";
import { getApiErrorMessage } from "../../identity";
import { useTranslation } from "react-i18next";

interface AddCustomBOQItemDialogProps {
  boqVersionId: string;
  onClose: () => void;
}

export function AddCustomBOQItemDialog({ boqVersionId, onClose }: AddCustomBOQItemDialogProps) {
  const { t } = useTranslation();
  const addItem = useAddCustomBOQItem(boqVersionId);
  const { showToast } = useToast();

  const [materialName, setMaterialName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitRate, setUnitRate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const cls = "mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    addItem.mutate(
      {
        material_name: materialName.trim(),
        category: category.trim() || null,
        unit: unit.trim(),
        quantity: Number(quantity),
        unit_rate: unitRate === "" ? null : Number(unitRate),
      },
      {
        onSuccess: () => {
          onClose();
          showToast({
            tone: "success",
            title: t("boq.addItem.successToast", { name: materialName.trim() }),
          });
        },
        onError: (mutationError) =>
         setError(getApiErrorMessage(mutationError, t("boq.addItem.error"))),
        },
      );
    }

  return (
    <Modal title={t("boq.addItem.title")} description={t("boq.addItem.description")} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.addItem.descriptionLabel")} *</span>
          <input className={cls} required value={materialName} onChange={(e) => setMaterialName(e.target.value)} placeholder={t("boq.addItem.descriptionPlaceholder")} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.addItem.category")}</span>
            <input className={cls} value={category} onChange={(e) => setCategory(e.target.value)} placeholder={t("boq.addItem.optional")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">{t("boq.addItem.unit")} *</span>
            <input className={cls} required value={unit} onChange={(e) => setUnit(e.target.value)} placeholder={t("boq.addItem.optional")} />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              {t("boq.addItem.quantity")} *
            </span>
            <input className={cls} required type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)}/>
          </label>

          <label className="block">
           <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
             {t("boq.addItem.rate")}
           </span>
           <input
            className={cls} type="number" step="any" value={unitRate} onChange={(e) => setUnitRate(e.target.value)}
              placeholder={t("boq.addItem.optional")}/>
          </label>
        </div>

        {error ? <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={addItem.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={addItem.isPending || !materialName.trim() || !unit.trim() || quantity === ""}>
            {addItem.isPending ? t("boq.addItem.adding") : t("boq.addItem.add")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}