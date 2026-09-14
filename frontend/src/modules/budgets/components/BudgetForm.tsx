import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, Icon, inputClass, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import { useSaveBudget } from "../hooks";
import type { Budget, BudgetCategoryInput } from "../types/budget.types";
import { useTranslation } from "react-i18next";

interface BudgetFormProps {
  projectId: string;
  budget: Budget | null;
  onClose: () => void;
}

export function BudgetForm({ projectId, budget, onClose }: BudgetFormProps) {
  const { t } = useTranslation();
  const saveBudget = useSaveBudget();
  const { showToast } = useToast();

  const [approvedAmount, setApprovedAmount] = useState(
    budget ? String(budget.approved_amount) : "",
  );
  const [currency, setCurrency] = useState(budget?.currency ?? "PKR");
  const [notes, setNotes] = useState(budget?.notes ?? "");
  const [categories, setCategories] = useState<BudgetCategoryInput[]>(
    budget?.categories.map((category) => ({
      name: category.name,
      allocated_amount: Number(category.allocated_amount),
    })) ?? [],
  );
  const [error, setError] = useState<string | null>(null);

  function updateCategory(index: number, patch: Partial<BudgetCategoryInput>) {
    setCategories((current) =>
      current.map((category, i) => (i === index ? { ...category, ...patch } : category)),
    );
  }

  function removeCategory(index: number) {
    setCategories((current) => current.filter((_, i) => i !== index));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    saveBudget.mutate(
      {
        project_id: projectId,
        approved_amount: Number(approvedAmount),
        currency,
        notes: notes.trim() || null,
        categories: categories.filter((category) => category.name.trim()),
      },
      {
        onSuccess: () => {
          onClose();
          showToast({ tone: "success", title: budget ? t("budgets.form.updated") : t("budgets.form.set") });
        },
        onError: () => setError(t("budgets.form.saveError")),
      },
    );
  }

  return (
    <Modal
      title={budget ? t("budgets.form.editTitle") : t("budgets.form.createTitle")}
      description={t("budgets.form.description")}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("budgets.form.approvedAmount")}>
            <input
              type="number"
              step="any"
              min="0"
              required
              className={inputClass}
              value={approvedAmount}
              onChange={(event) => setApprovedAmount(event.target.value)}
            />
          </Field>

          <Field label={t("budgets.form.currency")} hint={t("budgets.form.currencyHint")}>
            <input
              className={inputClass}
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              minLength={3}
              maxLength={3}
              required
            />
          </Field>
        </div>

        <Field label={t("budgets.form.notes")}>
          <textarea
            className={`${inputClass} resize-y`}
            rows={3}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder={t("budgets.form.notesPlaceholder")}
          />
        </Field>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">
              {t("budgets.form.categoryBreakdown")}
            </span>

            <button
              type="button"
              onClick={() => setCategories((current) => [...current, { name: "", allocated_amount: 0 }])}
              className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline"
            >
              {t("budgets.form.addCategory")}
            </button>
          </div>

          {categories.length === 0 ? (
            <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
              {t("budgets.form.noCategories")}
            </div>
          ) : (
            <div className="space-y-2">
              {categories.map((category, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    className={inputClass}
                    placeholder={t("budgets.form.categoryNamePlaceholder")}
                    value={category.name}
                    onChange={(event) => updateCategory(index, { name: event.target.value })}
                  />
                  <input
                    type="number"
                    step="any"
                    min="0"
                    className={`${inputClass} w-40`}
                    placeholder={t("budgets.form.amountPlaceholder")}
                    value={category.allocated_amount || ""}
                    onChange={(event) =>
                      updateCategory(index, { allocated_amount: Number(event.target.value) })
                    }
                  />
                  <button
                    type="button"
                    onClick={() => removeCategory(index)}
                    aria-label={t("budgets.form.removeCategory", { name: category.name || t("budgets.form.categoryFallback") })}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-border)] text-[var(--color-text-secondary)] outline-none transition hover:bg-[var(--color-surface-muted)] focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)]"
                  >
                    <Icon name="x" size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={saveBudget.isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" variant="primary" disabled={saveBudget.isPending || !approvedAmount}>
            {saveBudget.isPending ? t("common.saving") : t("budgets.form.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}