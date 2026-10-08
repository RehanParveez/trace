import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, TableShell, Toggle, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { formatCurrency } from "../../utils/drawings-boq.utils";
import { useDeleteRateItem, useRateItems } from "../hooks";
import type { RateBook, RateItem } from "../types/pricing.types";
import { isBookEditable } from "../utils/pricing.utils";
import { RateImportDialog } from "./RateImportDialog";
import { RateItemFormDialog } from "./RateItemFormDialog";

export function RateItemsPanel({ book, canManage }: { book: RateBook; canManage: boolean }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const editable = canManage && isBookEditable(book);

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [trade, setTrade] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [formItem, setFormItem] = useState<RateItem | "new" | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [removing, setRemoving] = useState<RateItem | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(search.trim()), 300);
    return () => window.clearTimeout(handle);
  }, [search]);

  const query = useRateItems(book.id, { q: debounced, trade: trade.trim(), include_inactive: includeInactive });
  const unfiltered = useRateItems(book.id, {});
  const deleteItem = useDeleteRateItem(book.id);

  const trades = useMemo(() => {
    const set = new Set<string>();
    for (const row of unfiltered.items) if (row.trade) set.add(row.trade);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [unfiltered.items]);

  function confirmRemove() {
    if (!removing) return;
    setRemoveError(null);
    deleteItem.mutate(removing.id, {
      onSuccess: () => {
        showToast({ tone: "success", title: t("pricing.items.removedToast", "Rate removed") });
        setRemoving(null);
      },
      onError: (e) => setRemoveError(getApiErrorMessage(e, t("pricing.items.removeError", "Couldn't remove this rate."))),
    });
  }

  const inputSmall =
    "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]";

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.items.eyebrow", "RATES")}
        title={t("pricing.items.title", "Rates")}
        description={
          editable
            ? t("pricing.items.descEditable", "Add rates one at a time, paste a block from a spreadsheet, or import a CSV.")
            : t("pricing.items.descFrozen", "This book can't be edited. Start a new version (or copy it into your organisation) to change rates.")
        }
        action={
          editable ? (
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>
                {t("pricing.items.import", "Import")}
              </Button>
              <Button variant="primary" size="sm" onClick={() => setFormItem("new")}>
                {t("pricing.items.add", "Add rate")}
              </Button>
            </div>
          ) : null
        }
      />

      <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] p-4">
        <input
          className={`${inputSmall} w-56`}
          value={search}
          placeholder={t("pricing.items.search", "Search code or description")}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className={inputSmall} value={trade} onChange={(e) => setTrade(e.target.value)}>
          <option value="">{t("pricing.items.allTrades", "All trades")}</option>
          {trades.map((tr) => (
            <option key={tr} value={tr}>{tr}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
          <Toggle
            checked={includeInactive}
            onChange={() => setIncludeInactive((v) => !v)}
            label={t("pricing.items.showInactive", "Show inactive")}
          />
          {t("pricing.items.showInactive", "Show inactive")}
        </label>
      </div>

      {query.isLoading ? (
        <LoadingState label={t("pricing.items.loading", "Loading rates…")} />
      ) : query.isError ? (
        <ErrorState title={t("pricing.items.loadError", "We couldn't load the rates")} onRetry={() => void query.refetch()} />
      ) : query.items.length === 0 ? (
        <EmptyState
          icon="budget"
          title={debounced || trade ? t("pricing.items.noMatch", "No rates match") : t("pricing.items.emptyTitle", "No rates yet")}
          description={
            editable
              ? t("pricing.items.emptyDesc", "Add the first rate, or import a CSV, then publish the book to price BOQs with it.")
              : t("pricing.items.emptyFrozen", "This rate book has no rates.")
          }
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[860px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("pricing.items.colCode", "Work item")}</th>
                <th className="px-4 py-3">{t("pricing.items.colDescription", "Description")}</th>
                <th className="px-4 py-3">{t("pricing.items.colTrade", "Trade")}</th>
                <th className="px-4 py-3">{t("pricing.items.colUnit", "Unit")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.items.colRate", "Rate")}</th>
                <th className="px-4 py-3">{t("pricing.items.colRef", "CSR ref")}</th>
                {editable ? <th className="px-4 py-3 text-right">{t("pricing.items.colActions", "Actions")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {query.items.map((row) => (
                <tr key={row.id} className={`border-t border-[var(--color-border)] ${row.is_active ? "" : "opacity-60"}`}>
                  <td className="px-4 py-3 font-mono text-[12.5px] font-semibold">
                    {row.work_item_code}
                    {row.analysis_id ? (
                      <span className="ml-2 align-middle">
                        <Badge tone="blue">{t("pricing.items.fromAnalysis", "Analysis")}</Badge>
                      </span>
                    ) : null}
                    {!row.is_active ? (
                      <span className="ml-2 align-middle">
                        <Badge tone="slate">{t("pricing.items.inactive", "Inactive")}</Badge>
                      </span>
                    ) : null}
                  </td>
                  <td className="max-w-[320px] px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">{row.description ?? "—"}</td>
                  <td className="px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">{row.trade ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-[12.5px]">{row.unit}</td>
                  <td className="px-4 py-3 text-right font-mono text-[12.5px]">{formatCurrency(row.rate)}</td>
                  <td className="px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">{row.csr_ref ?? "—"}</td>
                  {editable ? (
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setFormItem(row)}>{t("common.edit", "Edit")}</Button>
                        <Button variant="ghost" size="sm" onClick={() => { setRemoveError(null); setRemoving(row); }}>
                          {t("pricing.items.remove", "Remove")}
                        </Button>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {query.hasNextPage ? (
        <div className="flex justify-center border-t border-[var(--color-border)] p-4">
          <Button variant="secondary" size="sm" onClick={() => void query.fetchNextPage()} disabled={query.isFetchingNextPage}>
            {query.isFetchingNextPage ? t("common.loading", "Loading…") : t("pricing.loadMore", "Load more")}
          </Button>
        </div>
      ) : null}

      {formItem ? (
        <RateItemFormDialog
          bookId={book.id}
          item={formItem === "new" ? null : formItem}
          trades={trades}
          onClose={() => setFormItem(null)}
        />
      ) : null}
      {importOpen ? <RateImportDialog bookId={book.id} onClose={() => setImportOpen(false)} /> : null}
      {removing ? (
        <ConfirmDialog
          title={t("pricing.items.removeTitle", "Remove this rate?")}
          description={t("pricing.items.removeDesc", "{{code}} ({{unit}}) will be deleted from this draft.", {
            code: removing.work_item_code, unit: removing.unit,
          })}
          confirmLabel={t("pricing.items.remove", "Remove")}
          pending={deleteItem.isPending}
          error={removeError}
          onConfirm={confirmRemove}
          onClose={() => setRemoving(null)}
        />
      ) : null}
    </Panel>
  );
}
