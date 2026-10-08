import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {Badge, Button, ErrorState, LoadingState, PageHeader, StatCard, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage, usePermissionKeys } from "../../../identity";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { PRICING_PERMISSIONS } from "../permissions";
import {useArchiveRateBook, useDeleteRateBook, useNewRateBookVersion, usePublishRateBook, useRateBook,
} from "../hooks";
import {RATE_BOOKS_PATH, RATE_BOOK_STATUS_LABEL, formatDate, isBookEditable, rateBookPath, rateBookStatusTone,
} from "../utils/pricing.utils";
import { AnalysesPanel } from "../components/AnalysesPanel";
import { EscalationsPanel } from "../components/EscalationsPanel";
import { RateBookFormDialog } from "../components/RateBookFormDialog";
import { RateItemsPanel } from "../components/RateItemsPanel";

type Tab = "rates" | "escalations" | "analyses";
type Action = "publish" | "version" | "archive" | "delete";

export function RateBookDetailPage() {
  const { t } = useTranslation();
  const { bookId = "" } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(PRICING_PERMISSIONS.DRAWING_READ);
  const canManage = permissions.includes(PRICING_PERMISSIONS.RATEBOOK_MANAGE);

  const query = useRateBook(bookId);
  const publish = usePublishRateBook();
  const newVersion = useNewRateBookVersion();
  const archive = useArchiveRateBook();
  const remove = useDeleteRateBook();

  const [tab, setTab] = useState<Tab>("rates");
  const [action, setAction] = useState<Action | null>(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!canRead && permissions.length > 0) {
    return <ErrorState title={t("pricing.books.unavailable", "Rate books unavailable")} description={t("pricing.noPermission", "You don't have permission to view this.")} />;
  }
  if (query.isLoading) return <LoadingState label={t("pricing.book.loading", "Loading rate book…")} />;
  if (query.isError || !query.data) {
    return <ErrorState title={t("pricing.book.loadError", "We couldn't load this rate book")} onRetry={() => void query.refetch()} />;
  }

  const book = query.data;
  const writable = canManage && !book.is_system;
  const editable = canManage && isBookEditable(book);
  const pending = publish.isPending || newVersion.isPending || archive.isPending || remove.isPending;

  const tabs: Array<{ id: Tab; label: string; count: number }> = [
    { id: "rates", label: t("pricing.book.tabRates", "Rates"), count: book.item_count },
    { id: "escalations", label: t("pricing.book.tabEscalations", "Escalations"), count: book.escalation_count },
    { id: "analyses", label: t("pricing.book.tabAnalyses", "Analyses"), count: book.analysis_count },
  ];

  function run() {
    if (!action) return;
    setError(null);
    const fail = (e: unknown) => setError(getApiErrorMessage(e, t("pricing.book.actionError", "That didn't work. Please try again.")));

    if (action === "publish") {
      publish.mutate(book.id, {
        onSuccess: () => { showToast({ tone: "success", title: t("pricing.book.publishedToast", "Rate book published") }); setAction(null); },
        onError: fail,
      });
    } else if (action === "version") {
      newVersion.mutate(book.id, {
        onSuccess: (created) => {
          showToast({ tone: "success", title: t("pricing.book.versionToast", "New draft version created") });
          setAction(null);
          navigate(rateBookPath(created.id));
        },
        onError: fail,
      });
    } else if (action === "archive") {
      archive.mutate(book.id, {
        onSuccess: () => { showToast({ tone: "success", title: t("pricing.book.archivedToast", "Rate book archived") }); setAction(null); },
        onError: fail,
      });
    } else {
      remove.mutate(book.id, {
        onSuccess: () => {
          showToast({ tone: "success", title: t("pricing.book.deletedToast", "Draft deleted") });
          navigate(RATE_BOOKS_PATH);
        },
        onError: fail,
      });
    }
  }

  const confirm: Record<Action, { title: string; body: string; label: string }> = {
    publish: {
      title: t("pricing.book.publishTitle", "Publish {{code}} v{{v}}?", { code: book.code, v: book.immutable_version }),
      body: t(
        "pricing.book.publishBody",
        "Publishing freezes the {{n}} rates and the details. Any earlier active version of this book becomes superseded. To change a published book you start a new version.",
        { n: book.item_count },
      ),
      label: t("pricing.book.publish", "Publish"),
    },
    version: {
      title: t("pricing.book.versionTitle", "Start a new version?"),
      body: t("pricing.book.versionBody", "A draft copy of this book (rates, escalations and analyses) is created so you can change it without touching the published version."),
      label: t("pricing.book.newVersion", "New version"),
    },
    archive: {
      title: t("pricing.book.archiveTitle", "Archive this rate book?"),
      body: t("pricing.book.archiveBody", "It will no longer be offered for pricing. BOQs already priced from it keep their recorded rates."),
      label: t("pricing.book.archive", "Archive"),
    },
    delete: {
      title: t("pricing.book.deleteTitle", "Delete this draft?"),
      body: t("pricing.book.deleteBody", "The draft and its rates are removed for good. A book that priced any BOQ line can't be deleted."),
      label: t("pricing.book.delete", "Delete"),
    },
  };

  return (
    <div className="space-y-7">
      <div>
        <Link to={RATE_BOOKS_PATH} className="text-[12.5px] font-semibold text-[var(--color-info)] hover:underline">
          ← {t("pricing.book.back", "All rate books")}
        </Link>
      </div>

      <PageHeader
        eyebrow={t("pricing.eyebrow", "PRICING")}
        title={book.name}
        description={`${book.code} · v${book.immutable_version}${book.edition ? ` · ${book.edition}` : ""}${book.is_system ? ` · ${t("pricing.system", "System")}` : ""}`}
        actions={
          <>
            <Badge tone={rateBookStatusTone(book.status)}>{t(`pricing.status.${book.status}`, RATE_BOOK_STATUS_LABEL[book.status])}</Badge>
            {editable ? (
              <>
                <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>{t("pricing.book.editDetails", "Edit details")}</Button>
                <Button variant="primary" size="sm" onClick={() => { setError(null); setAction("publish"); }}>{t("pricing.book.publish", "Publish")}</Button>
                <Button variant="danger" size="sm" onClick={() => { setError(null); setAction("delete"); }}>{t("pricing.book.delete", "Delete")}</Button>
              </>
            ) : null}
            {writable && (book.status === "ACTIVE" || book.status === "SUPERSEDED") ? (
              <>
                <Button variant="primary" size="sm" onClick={() => { setError(null); setAction("version"); }}>{t("pricing.book.newVersion", "New version")}</Button>
                <Button variant="secondary" size="sm" onClick={() => { setError(null); setAction("archive"); }}>{t("pricing.book.archive", "Archive")}</Button>
              </>
            ) : null}
          </>
        }
      />

      {book.is_system ? (
        <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-info-bg)] px-4 py-3 text-[13px] text-[var(--color-text-secondary)]">
          {t("pricing.book.systemNote", "This is a system book and is read-only. Use “Copy to my organisation” on the rate books page to make an editable draft.")}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-4">
        <StatCard label={t("pricing.book.statRates", "Rates")} value={book.item_count} note={t("pricing.book.statRatesNote", "Priced work items")} icon="budget" tone="blue" />
        <StatCard label={t("pricing.book.statEsc", "Escalations")} value={book.escalation_count} note={t("pricing.book.statEscNote", "Dated factors")} icon="trend" tone="gold" />
        <StatCard label={t("pricing.book.statAnalyses", "Analyses")} value={book.analysis_count} note={t("pricing.book.statAnalysesNote", "Rates with working")} icon="calendar" tone="blue" />
        <StatCard
          label={t("pricing.book.statEffective", "Effective")}
          value={book.effective_from ? formatDate(book.effective_from) : "—"}
          note={book.effective_to ? t("pricing.book.until", "until {{date}}", { date: formatDate(book.effective_to) }) : t("pricing.book.openEnded", "No end date")}
          icon="clock"
          tone="green"
        />
      </div>

      {book.status !== "DRAFT" ? (
        <div className="grid gap-x-8 gap-y-1 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)] sm:grid-cols-2">
          <div>{t("pricing.book.published", "Published")}: {formatDate(book.published_at)}</div>
          <div className="truncate" title={book.content_hash ?? undefined}>
            {t("pricing.book.hash", "Content hash")}: <span className="font-mono">{book.content_hash ? book.content_hash.slice(0, 16) : "—"}</span>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-[8px] border px-3 py-2 text-[12.5px] font-semibold ${
              tab === item.id ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"
            }`}
          >
            {item.label} <span className="text-[var(--color-text-muted)]">({item.count})</span>
          </button>
        ))}
      </div>

      {tab === "rates" ? <RateItemsPanel book={book} canManage={canManage} /> : null}
      {tab === "escalations" ? <EscalationsPanel book={book} canManage={canManage} /> : null}
      {tab === "analyses" ? <AnalysesPanel book={book} canManage={canManage} /> : null}

      {editing ? <RateBookFormDialog mode="edit" book={book} onClose={() => setEditing(false)} /> : null}
      {action ? (
        <ConfirmDialog
          title={confirm[action].title}
          description={confirm[action].body}
          confirmLabel={confirm[action].label}
          pending={pending}
          error={error}
          onConfirm={run}
          onClose={() => setAction(null)}
        />
      ) : null}
    </div>
  );
}
