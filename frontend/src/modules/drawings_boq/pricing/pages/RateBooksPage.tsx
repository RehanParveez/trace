import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../../identity";
import { PRICING_PERMISSIONS } from "../permissions";
import { useRateBooks } from "../hooks";
import type { RateBook, RateBookOwner, RateBookStatus } from "../types/pricing.types";
import { rateBookPath } from "../utils/pricing.utils";
import { RateBookFormDialog } from "../components/RateBookFormDialog";
import { RateBookTable } from "../components/RateBookTable";

export function RateBooksPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PRICING_PERMISSIONS.DRAWING_READ);
  const canManage = permissions.includes(PRICING_PERMISSIONS.RATEBOOK_MANAGE);

  const [owner, setOwner] = useState<RateBookOwner>("all");
  const [status, setStatus] = useState<RateBookStatus | "">("");
  const [creating, setCreating] = useState(false);
  const [copyFrom, setCopyFrom] = useState<RateBook | null>(null);

  const query = useRateBooks({ owner, status: status || null });
  const summary = useRateBooks({});

  if (!canRead && permissions.length > 0) {
    return (
      <ErrorState
        title={t("pricing.books.unavailable", "Rate books unavailable")}
        description={t("pricing.noPermission", "You don't have permission to view this.")}
      />
    );
  }
  if (query.isLoading) return <LoadingState label={t("pricing.books.loading", "Loading rate books…")} />;
  if (query.isError) {
    return <ErrorState title={t("pricing.books.loadError", "We couldn't load rate books")} onRetry={() => void query.refetch()} />;
  }

  const all = summary.books;
  const active = all.filter((b) => b.status === "ACTIVE").length;
  const drafts = all.filter((b) => b.status === "DRAFT").length;
  const system = all.filter((b) => b.is_system && b.status === "ACTIVE").length;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={t("pricing.eyebrow", "PRICING")}
        title={t("pricing.books.pageTitle", "Rate books")}
        description={t(
          "pricing.books.pageDesc",
          "Schedules of rates that price your BOQs. Published versions are frozen, escalations are dated, and every priced line records which book and factor it used.",
        )}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label={t("pricing.books.statActive", "Active books")} value={active} note={t("pricing.books.statActiveNote", "Used to price BOQs")} icon="check" tone="green" />
        <StatCard label={t("pricing.books.statDrafts", "Drafts")} value={drafts} note={t("pricing.books.statDraftsNote", "Editable, not yet published")} icon="alert" tone={drafts > 0 ? "gold" : "blue"} />
        <StatCard label={t("pricing.books.statSystem", "System books")} value={system} note={t("pricing.books.statSystemNote", "Read-only, copy to customise")} icon="budget" tone="blue" />
      </div>

      <RateBookTable
        books={query.books}
        owner={owner}
        status={status}
        canManage={canManage}
        hasMore={Boolean(query.hasNextPage)}
        loadingMore={query.isFetchingNextPage}
        onOwnerChange={setOwner}
        onStatusChange={setStatus}
        onLoadMore={() => void query.fetchNextPage()}
        onCreate={() => { setCopyFrom(null); setCreating(true); }}
        onOpen={(book) => navigate(rateBookPath(book.id))}
        onCopy={(book) => { setCopyFrom(book); setCreating(true); }}
      />

      {creating ? (
        <RateBookFormDialog
          mode="create"
          copyFrom={copyFrom}
          onClose={() => setCreating(false)}
          onSaved={(book) => navigate(rateBookPath(book.id))}
        />
      ) : null}
    </div>
  );
}
