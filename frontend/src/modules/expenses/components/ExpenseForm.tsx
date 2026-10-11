import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { useCreateExpense } from "../hooks";
import { IDENTITY_PERMISSIONS, usePermissionKeys, getApiErrorMessage } from "../../identity";
import { useProjectBudget } from "../../budgets/hooks";
import { useTranslation } from "react-i18next";
import { todayLocal } from "../../../shared/utils/date";

interface ExpenseFormProps {
  projectId: string;
  onClose: () => void;
}

export function ExpenseForm({ projectId, onClose }: ExpenseFormProps) {
  const createExpense = useCreateExpense();
  const { showToast } = useToast();
  const { t } = useTranslation();

  const permissions = usePermissionKeys();
  const canViewBudget = permissions.includes(IDENTITY_PERMISSIONS.BUDGET_READ);
  const budgetQuery = useProjectBudget(canViewBudget ? projectId : undefined);
  const budgetCategories = budgetQuery.data?.categories ?? [];
  const OTHER = "__other__";
  const [budgetCategoryId, setBudgetCategoryId] = useState("");
  const [category, setCategory] = useState("");
  const useListedCategory = budgetCategories.length > 0 && budgetCategoryId !== OTHER;
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseDate, setExpenseDate] = useState(() => todayLocal());
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createExpense.mutate(
      {
        project_id: projectId,
        ...(useListedCategory
          ? { budget_category_id: budgetCategoryId }
          : { category: category.trim() }),
        description: description.trim() || null,
        amount: Number(amount),
        expense_date: expenseDate,
      },
      {
        onSuccess: () => {
          onClose();
          showToast({ tone: "success", title: t("expenses.form.recorded") });
        },
        onError: (err) => setError(getApiErrorMessage(err, t("expenses.form.createError"))),
      },
    );
  }

  return (
    <Modal title={t("expenses.form.title")} description={t("expenses.form.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("expenses.form.category")} hint={budgetCategories.length > 0 ? t("expenses.form.categoryLinkedHint") : undefined}>
            {budgetCategories.length > 0 ? (
              <>
                <select required className={inputClass} value={budgetCategoryId} onChange={(e) => setBudgetCategoryId(e.target.value)}>
                  <option value="">{t("expenses.form.categorySelect")}</option>
                  {budgetCategories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                  <option value={OTHER}>{t("expenses.form.categoryOther")}</option>
                </select>
                {budgetCategoryId === OTHER ? (
                  <input required className={`${inputClass} mt-2`} value={category} onChange={(e) => setCategory(e.target.value)} placeholder={t("expenses.form.categoryPlaceholder")} />
                ) : null}
              </>
            ) : (
              <input required className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)} placeholder={t("expenses.form.categoryPlaceholder")} />
            )}
          </Field>
          <Field label={t("expenses.form.amount")}>
            <input type="number" step="any" min="0.01" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
        </div>

        <Field label={t("expenses.form.date")}>
          <input type="date" required className={inputClass} value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
        </Field>

        <Field label={t("expenses.form.descriptionLabel")}>
          <textarea className={`${inputClass} resize-y`} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder={t("expenses.form.descriptionPlaceholder")} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createExpense.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={createExpense.isPending || !amount || (useListedCategory ? !budgetCategoryId : !category.trim())}>
            {createExpense.isPending ? t("common.saving") : t("expenses.form.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}