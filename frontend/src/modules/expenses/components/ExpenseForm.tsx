import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal } from "../../organizations/components/OrganizationUi";
import { useCreateExpense } from "../hooks";

interface ExpenseFormProps {
  projectId: string;
  onClose: () => void;
}

export function ExpenseForm({ projectId, onClose }: ExpenseFormProps) {
  const createExpense = useCreateExpense();

  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseDate, setExpenseDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createExpense.mutate(
      {
        project_id: projectId,
        category: category.trim(),
        description: description.trim() || null,
        amount: Number(amount),
        expense_date: expenseDate,
      },
      {
        onSuccess: onClose,
        onError: () => setError("Couldn't record this expense. Please try again."),
      },
    );
  }

  return (
    <Modal title="Record expense" description="Log a project expense for review and approval." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Category">
            <input required className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Site transport" />
          </Field>
          <Field label="Amount (PKR)">
            <input type="number" step="any" min="0.01" required className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
        </div>

        <Field label="Expense date">
          <input type="date" required className={inputClass} value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
        </Field>

        <Field label="Description">
          <textarea className={`${inputClass} resize-y`} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional details for this expense" />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createExpense.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createExpense.isPending || !category.trim() || !amount}>
            {createExpense.isPending ? "Saving…" : "Record expense"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}