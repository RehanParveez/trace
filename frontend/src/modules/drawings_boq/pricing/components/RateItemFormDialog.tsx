import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button, Field, inputClass, Modal, Toggle, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { WORK_ITEM_SUGGESTIONS } from "../../utils/drawings-boq.utils";
import { useAddRateItem, useUpdateRateItem } from "../hooks";
import type { RateItem } from "../types/pricing.types";
import { emptyToNull, parseNonNegative } from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface RateItemFormDialogProps {
  bookId: string;
  item?: RateItem | null;
  trades: string[];
  onClose: () => void;
}

const UNIT_SUGGESTIONS = ["m3", "m2", "m", "kg", "nos", "cft", "sft", "rft", "ton", "ls"];

export function RateItemFormDialog({ bookId, item, trades, onClose }: RateItemFormDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const addItem = useAddRateItem(bookId);
  const updateItem = useUpdateRateItem(bookId);
  const editing = Boolean(item);

  const [code, setCode] = useState(item?.work_item_code ?? "");
  const [unit, setUnit] = useState(item?.unit ?? "m3");
  const [rate, setRate] = useState(item ? String(Number(item.rate)) : "");
  const [trade, setTrade] = useState(item?.trade ?? "");
  const [csrRef, setCsrRef] = useState(item?.csr_ref ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [specification, setSpecification] = useState(item?.specification ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const pending = addItem.isPending || updateItem.isPending;
  const rateValue = parseNonNegative(rate);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (rateValue === null) {
      setError(t("pricing.item.rateInvalid", "Enter a rate of zero or more."));
      return;
    }
    const common = {
      rate: rateValue,
      trade: emptyToNull(trade),
      csr_ref: emptyToNull(csrRef),
      description: emptyToNull(description),
      specification: emptyToNull(specification),
    };

    if (item) {
      updateItem.mutate(
        { itemId: item.id, payload: { ...common, is_active: isActive } },
        {
          onSuccess: () => {
            showToast({ tone: "success", title: t("pricing.item.savedToast", "Rate updated") });
            onClose();
          },
          onError: (e) => setError(getApiErrorMessage(e, t("pricing.item.saveError", "Couldn't save this rate."))),
        },
      );
      return;
    }

    addItem.mutate(
      { ...common, work_item_code: code.trim().toUpperCase(), unit: unit.trim() },
      {
        onSuccess: () => {
          showToast({ tone: "success", title: t("pricing.item.addedToast", "Rate added") });
          onClose();
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.item.addError", "Couldn't add this rate."))),
      },
    );
  }

  return (
    <Modal
      title={editing ? t("pricing.item.editTitle", "Edit rate") : t("pricing.item.addTitle", "Add a rate")}
      description={t(
        "pricing.item.desc",
        "A rate prices one work item in one unit. A BOQ line matches on the work item code, and on the unit or one that converts to it.",
      )}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("pricing.item.code", "Work item code")}>
            <input
              required
              disabled={editing}
              list="pricing-work-item-codes"
              className={inputClass}
              value={code}
              maxLength={50}
              onChange={(e) => setCode(e.target.value)}
              placeholder="RCC-M20"
            />
            <datalist id="pricing-work-item-codes">
              {WORK_ITEM_SUGGESTIONS.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </Field>
          <Field label={t("pricing.item.unit", "Unit")}>
            <input
              required
              disabled={editing}
              list="pricing-units"
              className={inputClass}
              value={unit}
              maxLength={20}
              onChange={(e) => setUnit(e.target.value)}
            />
            <datalist id="pricing-units">
              {UNIT_SUGGESTIONS.map((u) => (
                <option key={u} value={u} />
              ))}
            </datalist>
          </Field>
          <Field label={t("pricing.item.rate", "Rate")}>
            <input
              required
              type="number"
              min="0"
              step="0.01"
              className={inputClass}
              value={rate}
              onChange={(e) => setRate(e.target.value)}
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label={t("pricing.item.trade", "Trade")}
            hint={t("pricing.item.tradeHint", "Escalations can target a trade, e.g. Steel or Concrete.")}
          >
            <input list="pricing-trades" className={inputClass} value={trade} maxLength={80} onChange={(e) => setTrade(e.target.value)} />
            <datalist id="pricing-trades">
              {trades.map((tr) => (
                <option key={tr} value={tr} />
              ))}
            </datalist>
          </Field>
          <Field label={t("pricing.item.csrRef", "CSR reference")}>
            <input className={inputClass} value={csrRef} maxLength={80} onChange={(e) => setCsrRef(e.target.value)} />
          </Field>
        </div>

        <Field label={t("pricing.item.description", "Description")}>
          <input className={inputClass} value={description} maxLength={500} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label={t("pricing.item.specification", "Specification")}>
          <textarea className={`${inputClass} min-h-[64px]`} value={specification} onChange={(e) => setSpecification(e.target.value)} />
        </Field>

        {editing ? (
          <div className="flex items-center gap-3">
            <Toggle checked={isActive} onChange={() => setIsActive((v) => !v)} label={t("pricing.item.active", "Active")} />
            <span className="text-[13px] text-[var(--color-text-secondary)]">
              {isActive
                ? t("pricing.item.activeOn", "Active: used when pricing")
                : t("pricing.item.activeOff", "Inactive: ignored when pricing")}
            </span>
          </div>
        ) : null}

        <FormError message={error} />

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={pending}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button type="submit" variant="primary" disabled={pending || !code.trim() || !unit.trim() || rate === ""}>
            {pending ? t("common.saving", "Saving…") : editing ? t("pricing.item.save", "Save rate") : t("pricing.item.add", "Add rate")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
