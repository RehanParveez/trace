import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button, Field, inputClass, Modal, useToast } from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useCreateRateBook, useRateBooks, useUpdateRateBook } from "../hooks";
import type { RateBook } from "../types/pricing.types";
import { emptyToNull, rateBookTitle } from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface RateBookFormDialogProps {
  mode: "create" | "edit";
  book?: RateBook;
  copyFrom?: RateBook | null;
  onClose: () => void;
  onSaved?: (book: RateBook) => void;
}

export function RateBookFormDialog({ mode, book, copyFrom, onClose, onSaved }: RateBookFormDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const booksQuery = useRateBooks({});
  const createBook = useCreateRateBook();
  const updateBook = useUpdateRateBook(book?.id ?? "");

  const seed = mode === "edit" ? book : copyFrom;
  const [copyFromId, setCopyFromId] = useState(copyFrom?.id ?? "");
  const [code, setCode] = useState(mode === "edit" ? (book?.code ?? "") : (copyFrom?.code ?? ""));
  const [name, setName] = useState(seed?.name ?? "");
  const [edition, setEdition] = useState(seed?.edition ?? "");
  const [currency, setCurrency] = useState(seed?.currency ?? "PKR");
  const [jurisdiction, setJurisdiction] = useState(seed?.jurisdiction ?? "");
  const [province, setProvince] = useState(seed?.province ?? "");
  const [city, setCity] = useState(seed?.city ?? "");
  const [effectiveFrom, setEffectiveFrom] = useState(seed?.effective_from ?? "");
  const [effectiveTo, setEffectiveTo] = useState(seed?.effective_to ?? "");
  const [description, setDescription] = useState(seed?.description ?? "");
  const [error, setError] = useState<string | null>(null);

  const pending = createBook.isPending || updateBook.isPending;
  const rangeInvalid = Boolean(effectiveFrom && effectiveTo && effectiveTo < effectiveFrom);
  const copyOptions = booksQuery.books.filter((b) => b.status !== "ARCHIVED" || b.id === copyFrom?.id);

  function pickCopySource(id: string) {
    setCopyFromId(id);
    const source = copyOptions.find((b) => b.id === id);
    if (source) {
      setName((current) => current || source.name);
      setCode((current) => current || source.code);
      setEdition((current) => current || (source.edition ?? ""));
      setCurrency(source.currency);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (rangeInvalid) {
      setError(t("pricing.form.rangeInvalid", "The end date is before the start date."));
      return;
    }
    const details = {
      name: name.trim(),
      description: emptyToNull(description),
      edition: emptyToNull(edition),
      currency: currency.trim().toUpperCase() || "PKR",
      jurisdiction: emptyToNull(jurisdiction),
      province: emptyToNull(province),
      city: emptyToNull(city),
      effective_from: emptyToNull(effectiveFrom),
      effective_to: emptyToNull(effectiveTo),
    };

    if (mode === "edit" && book) {
      updateBook.mutate(details, {
        onSuccess: (saved) => {
          showToast({ tone: "success", title: t("pricing.form.savedToast", "Rate book updated") });
          onSaved?.(saved);
          onClose();
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.form.saveError", "Couldn't save this rate book."))),
      });
      return;
    }

    createBook.mutate(
      { ...details, code: code.trim().toUpperCase(), copy_from_id: copyFromId || null },
      {
        onSuccess: (created) => {
          showToast({ tone: "success", title: t("pricing.form.createdToast", "Draft rate book created") });
          onSaved?.(created);
          onClose();
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.form.createError", "Couldn't create this rate book."))),
      },
    );
  }

  return (
    <Modal
      title={mode === "edit" ? t("pricing.form.editTitle", "Edit rate book details") : t("pricing.form.createTitle", "New rate book")}
      description={
        mode === "edit"
          ? t("pricing.form.editDesc", "Only a draft can be edited. Publishing freezes the rates and the details.")
          : t("pricing.form.createDesc", "A draft you can fill with rates. Copy an existing book to start from its rates.")
      }
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        {mode === "create" ? (
          <Field
            label={t("pricing.form.copyFrom", "Copy rates from")}
            hint={t("pricing.form.copyFromHint", "System books are read-only. Copy one into your organisation to adjust it.")}
          >
            <select className={inputClass} value={copyFromId} onChange={(e) => pickCopySource(e.target.value)}>
              <option value="">{t("pricing.form.startEmpty", "Start empty")}</option>
              {copyOptions.map((b) => (
                <option key={b.id} value={b.id}>
                  {rateBookTitle(b)}
                  {b.is_system ? ` · ${t("pricing.system", "System")}` : ""}
                </option>
              ))}
            </select>
          </Field>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label={t("pricing.form.code", "Code")}
            hint={mode === "edit" ? t("pricing.form.codeLocked", "The code can't change.") : t("pricing.form.codeHint", "Versions of a book share one code, e.g. CSR-2025.")}
          >
            <input
              required
              disabled={mode === "edit"}
              className={inputClass}
              value={code}
              maxLength={50}
              onChange={(e) => setCode(e.target.value)}
              placeholder="CSR-2025"
            />
          </Field>
          <Field label={t("pricing.form.edition", "Edition")}>
            <input className={inputClass} value={edition} maxLength={50} onChange={(e) => setEdition(e.target.value)} placeholder="2025-26" />
          </Field>
        </div>

        <Field label={t("pricing.form.name", "Name")}>
          <input required className={inputClass} value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-4">
          <Field label={t("pricing.form.currency", "Currency")}>
            <input className={inputClass} value={currency} maxLength={3} onChange={(e) => setCurrency(e.target.value)} />
          </Field>
          <Field label={t("pricing.form.jurisdiction", "Jurisdiction")}>
            <input className={inputClass} value={jurisdiction} maxLength={50} onChange={(e) => setJurisdiction(e.target.value)} />
          </Field>
          <Field label={t("pricing.form.province", "Province")}>
            <input className={inputClass} value={province} maxLength={50} onChange={(e) => setProvince(e.target.value)} />
          </Field>
          <Field label={t("pricing.form.city", "City")}>
            <input className={inputClass} value={city} maxLength={100} onChange={(e) => setCity(e.target.value)} />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("pricing.form.effectiveFrom", "Effective from")}>
            <input type="date" className={inputClass} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field
            label={t("pricing.form.effectiveTo", "Effective to")}
            error={rangeInvalid ? t("pricing.form.rangeInvalid", "The end date is before the start date.") : undefined}
          >
            <input type="date" className={inputClass} value={effectiveTo} min={effectiveFrom || undefined} onChange={(e) => setEffectiveTo(e.target.value)} />
          </Field>
        </div>

        <Field label={t("pricing.form.description", "Description")}>
          <textarea className={`${inputClass} min-h-[72px]`} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>

        <FormError message={error} />

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={pending}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button type="submit" variant="primary" disabled={pending || !name.trim() || (mode === "create" && !code.trim()) || rangeInvalid}>
            {pending
              ? t("common.saving", "Saving…")
              : mode === "edit"
                ? t("pricing.form.save", "Save changes")
                : t("pricing.form.create", "Create draft")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
