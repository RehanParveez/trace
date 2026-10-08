import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, Panel, PanelHeader, TableShell } from "../../../organizations/components/OrganizationUi";
import type { RateBook, RateBookOwner, RateBookStatus } from "../types/pricing.types";
import {RATE_BOOK_STATUSES, RATE_BOOK_STATUS_LABEL, formatDate, rateBookStatusTone,
} from "../utils/pricing.utils";

interface RateBookTableProps {
  books: RateBook[];
  owner: RateBookOwner;
  status: RateBookStatus | "";
  canManage: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onOwnerChange: (owner: RateBookOwner) => void;
  onStatusChange: (status: RateBookStatus | "") => void;
  onLoadMore: () => void;
  onCreate: () => void;
  onOpen: (book: RateBook) => void;
  onCopy: (book: RateBook) => void;
}

const selectClass =
  "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-primary)]";

export function RateBookTable({
  books, owner, status, canManage, hasMore, loadingMore, onOwnerChange, onStatusChange, onLoadMore, onCreate, onOpen, onCopy,
}: RateBookTableProps) {
  const { t } = useTranslation();

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.books.eyebrow", "RATE BOOKS")}
        title={t("pricing.books.title", "Rate books")}
        description={t(
          "pricing.books.description",
          "Priced schedules of rates. System books (such as the CSR) are read-only; copy one into your organisation to adjust it. A published version is frozen so a priced BOQ can always be traced back to it.",
        )}
        action={
          canManage ? (
            <Button variant="primary" size="sm" onClick={onCreate}>
              {t("pricing.books.new", "New rate book")}
            </Button>
          ) : null
        }
      />

      <div className="flex flex-wrap gap-3 border-b border-[var(--color-border)] p-4">
        <label className="flex items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
          {t("pricing.books.owner", "Owner")}
          <select className={selectClass} value={owner} onChange={(e) => onOwnerChange(e.target.value as RateBookOwner)}>
            <option value="all">{t("pricing.books.ownerAll", "All")}</option>
            <option value="org">{t("pricing.books.ownerOrg", "My organisation")}</option>
            <option value="system">{t("pricing.books.ownerSystem", "System (CSR)")}</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
          {t("pricing.books.status", "Status")}
          <select className={selectClass} value={status} onChange={(e) => onStatusChange(e.target.value as RateBookStatus | "")}>
            <option value="">{t("pricing.books.statusAll", "Any status")}</option>
            {RATE_BOOK_STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`pricing.status.${s}`, RATE_BOOK_STATUS_LABEL[s])}
              </option>
            ))}
          </select>
        </label>
      </div>

      {books.length === 0 ? (
        <EmptyState
          icon="budget"
          title={t("pricing.books.emptyTitle", "No rate books match")}
          description={t(
            "pricing.books.emptyDesc",
            "Create a draft, or copy a system book into your organisation, to start pricing BOQs from a schedule of rates.",
          )}
          action={
            canManage ? (
              <Button variant="primary" size="sm" onClick={onCreate}>
                {t("pricing.books.new", "New rate book")}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[880px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("pricing.books.colBook", "Rate book")}</th>
                <th className="px-4 py-3">{t("pricing.books.colEdition", "Edition")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.books.colRates", "Rates")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.books.colEscalations", "Escalations")}</th>
                <th className="px-4 py-3">{t("pricing.books.colEffective", "Effective")}</th>
                <th className="px-4 py-3">{t("pricing.books.colStatus", "Status")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.books.colActions", "Actions")}</th>
              </tr>
            </thead>
            <tbody>
              {books.map((book) => (
                <tr key={book.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3.5">
                    <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{book.name}</div>
                    <div className="font-mono text-[11px] text-[var(--color-text-muted)]">
                      {book.code} · v{book.immutable_version}
                      {book.is_system ? ` · ${t("pricing.system", "System")}` : ""}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{book.edition ?? "—"}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{book.item_count}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px]">{book.escalation_count}</td>
                  <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">
                    {book.effective_from || book.effective_to
                      ? `${formatDate(book.effective_from)} → ${book.effective_to ? formatDate(book.effective_to) : t("pricing.openEnded", "open")}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3.5">
                    <Badge tone={rateBookStatusTone(book.status)}>
                      {t(`pricing.status.${book.status}`, RATE_BOOK_STATUS_LABEL[book.status])}
                    </Badge>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="secondary" size="sm" onClick={() => onOpen(book)}>
                        {t("pricing.books.open", "Open")}
                      </Button>
                      {canManage && book.status !== "DRAFT" ? (
                        <Button variant="ghost" size="sm" onClick={() => onCopy(book)}>
                          {book.is_system ? t("pricing.books.copyToOrg", "Copy to my organisation") : t("pricing.books.copy", "Copy")}
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}

      {hasMore ? (
        <div className="flex justify-center border-t border-[var(--color-border)] p-4">
          <Button variant="secondary" size="sm" onClick={onLoadMore} disabled={loadingMore}>
            {loadingMore ? t("common.loading", "Loading…") : t("pricing.loadMore", "Load more")}
          </Button>
        </div>
      ) : null}
    </Panel>
  );
}
