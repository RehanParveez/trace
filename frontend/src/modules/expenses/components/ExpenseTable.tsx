import { Fragment, useState } from "react";
import {Badge, Button, EmptyState, Field, inputClass, Panel, PanelHeader, TableShell,
} from "../../organizations/components/OrganizationUi";
import type { Expense } from "../types/expense.types";
import { formatExpenseAmount, formatExpenseDate, formatExpenseStatus, getExpenseStatusTone } from "../utils/expense.utils";
import { useApproveExpense, useRejectExpense } from "../hooks";

interface ExpenseTableProps {
  expenses: Expense[];
  canCreate: boolean;
  canApprove: boolean;
  onCreate: () => void;
}

export function ExpenseTable({ expenses, canCreate, canApprove, onCreate }: ExpenseTableProps) {
  const approveExpense = useApproveExpense();
  const rejectExpense = useRejectExpense();
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");

  return (
    <Panel>
      <PanelHeader
        eyebrow="PROJECT EXPENSES"
        title="Expenses"
        description="Costs logged against this project, pending or approved."
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>Record expense</Button> : null}
      />

      {expenses.length === 0 ? (
        <EmptyState
          icon="expenses"
          title="No expenses recorded yet"
          description="Project expenses will appear here once someone logs one."
          action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>Record expense</Button> : undefined}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3">Status</th>
                {canApprove ? <th className="px-4 py-3 text-right">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {expenses.map((expense) => (
                <Fragment key={expense.id}>
                  <tr className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                    <td className="px-4 py-3.5">
                      <span className="block text-[13.5px] font-semibold text-[var(--color-text-primary)]">{expense.category}</span>
                      {expense.description ? <span className="mt-0.5 block max-w-[280px] truncate text-[12px] text-[var(--color-text-secondary)]">{expense.description}</span> : null}
                    </td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatExpenseDate(expense.expense_date)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatExpenseAmount(expense.amount)}</td>
                    <td className="px-4 py-3.5"><Badge tone={getExpenseStatusTone(expense.status)}>{formatExpenseStatus(expense.status)}</Badge></td>
                    {canApprove ? (
                      <td className="px-4 py-3.5 text-right">
                        {expense.status === "PENDING" ? (
                          <Button variant="secondary" size="sm" onClick={() => setReviewingId(reviewingId === expense.id ? null : expense.id)}>
                            Review
                          </Button>
                        ) : (
                          <span className="text-[11px] text-[var(--color-text-muted)]">—</span>
                        )}
                      </td>
                    ) : null}
                  </tr>

                  {reviewingId === expense.id ? (
                    <tr className="border-t border-[var(--color-border)] bg-[var(--color-warning-bg)]">
                      <td colSpan={canApprove ? 5 : 4} className="px-4 py-4">
                        <Field label="Review note">
                          <textarea
                            className={`${inputClass} resize-y`}
                            rows={2}
                            value={reviewNote}
                            onChange={(e) => setReviewNote(e.target.value)}
                            placeholder="Optional"
                          />
                        </Field>
                        <div className="mt-3 flex justify-end gap-2">
                          <Button
                            variant="danger"
                            size="sm"
                            disabled={rejectExpense.isPending}
                            onClick={() =>
                              rejectExpense.mutate(
                                { expenseId: expense.id, payload: { note: reviewNote.trim() || null } },
                                { onSuccess: () => { setReviewingId(null); setReviewNote(""); } },
                              )
                            }
                          >
                            Reject
                          </Button>
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={approveExpense.isPending}
                            onClick={() =>
                              approveExpense.mutate(
                                { expenseId: expense.id, payload: { note: reviewNote.trim() || null } },
                                { onSuccess: () => { setReviewingId(null); setReviewNote(""); } },
                              )
                            }
                          >
                            Approve
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}