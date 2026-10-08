import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, TableShell, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { formatCurrency, formatQuantity } from "../../utils/drawings-boq.utils";
import { useAnalyses, useDeleteAnalysis } from "../hooks";
import type { RateAnalysis, RateBook } from "../types/pricing.types";
import { isBookEditable } from "../utils/pricing.utils";
import { AnalysisBreakdownDialog } from "./AnalysisBreakdownDialog";
import { AnalysisEditor } from "./AnalysisEditor";

export function AnalysesPanel({ book, canManage }: { book: RateBook; canManage: boolean }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const query = useAnalyses(book.id);
  const deleteAnalysis = useDeleteAnalysis(book.id);
  const editable = canManage && isBookEditable(book);

  const [editing, setEditing] = useState<RateAnalysis | "new" | null>(null);
  const [viewing, setViewing] = useState<RateAnalysis | null>(null);
  const [removing, setRemoving] = useState<RateAnalysis | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  if (editing) {
    return <AnalysisEditor book={book} analysis={editing === "new" ? null : editing} onClose={() => setEditing(null)} />;
  }

  function confirmRemove() {
    if (!removing) return;
    setRemoveError(null);
    deleteAnalysis.mutate(removing.id, {
      onSuccess: () => {
        showToast({ tone: "success", title: t("pricing.analyses.removedToast", "Analysis removed") });
        setRemoving(null);
      },
      onError: (e) => setRemoveError(getApiErrorMessage(e, t("pricing.analyses.removeError", "Couldn't remove this analysis."))),
    });
  }

  const rows = query.data ?? [];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.analyses.eyebrow", "RATE ANALYSIS")}
        title={t("pricing.analyses.title", "Rate analyses")}
        description={t(
          "pricing.analyses.desc",
          "How a composite rate is built from materials, labour and plant. Applying an analysis writes its rate into the book's rates under the same work item code.",
        )}
        action={
          editable ? (
            <Button variant="primary" size="sm" onClick={() => setEditing("new")}>
              {t("pricing.analyses.new", "New analysis")}
            </Button>
          ) : null
        }
      />

      {query.isLoading ? (
        <LoadingState label={t("pricing.analyses.loading", "Loading analyses…")} />
      ) : query.isError ? (
        <ErrorState title={t("pricing.analyses.loadError", "We couldn't load the analyses")} onRetry={() => void query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon="calendar"
          title={t("pricing.analyses.emptyTitle", "No rate analyses")}
          description={t("pricing.analyses.emptyDesc", "Rates can be typed in directly. Add an analysis when you want a rate to show its working.")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[780px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("pricing.analyses.colCode", "Analysis")}</th>
                <th className="px-4 py-3">{t("pricing.analyses.colWorkItem", "Work item")}</th>
                <th className="px-4 py-3">{t("pricing.analyses.colBasis", "Basis")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.analyses.colParts", "Parts")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.analyses.colRate", "Saved rate")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.analyses.colActions", "Actions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3.5">
                    <div className="font-mono text-[12.5px] font-semibold">{a.code}</div>
                    <div className="text-[12px] text-[var(--color-text-secondary)]">{a.description}</div>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[12.5px]">{a.work_item_code}</td>
                  <td className="px-4 py-3.5 text-[12.5px]">
                    {formatQuantity(a.basis_quantity)} {a.unit}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{a.components.length}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">
                    {a.computed_rate === null ? <Badge tone="gold">{t("pricing.analyses.notComputed", "Not saved")}</Badge> : `${formatCurrency(a.computed_rate)} / ${a.unit}`}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="secondary" size="sm" onClick={() => setViewing(a)}>
                        {t("pricing.analyses.breakdown", "Breakdown")}
                      </Button>
                      {editable ? (
                        <>
                          <Button variant="ghost" size="sm" onClick={() => setEditing(a)}>{t("common.edit", "Edit")}</Button>
                          <Button variant="ghost" size="sm" onClick={() => { setRemoveError(null); setRemoving(a); }}>
                            {t("pricing.analyses.remove", "Remove")}
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {viewing ? <AnalysisBreakdownDialog bookId={book.id} analysis={viewing} editable={editable} onClose={() => setViewing(null)} /> : null}
      {removing ? (
        <ConfirmDialog
          title={t("pricing.analyses.removeTitle", "Remove this analysis?")}
          description={t("pricing.analyses.removeDesc", "{{code}} will be deleted from this draft. A rate already applied from it stays in the book.", { code: removing.code })}
          confirmLabel={t("pricing.analyses.remove", "Remove")}
          pending={deleteAnalysis.isPending}
          error={removeError}
          onConfirm={confirmRemove}
          onClose={() => setRemoving(null)}
        />
      ) : null}
    </Panel>
  );
}
