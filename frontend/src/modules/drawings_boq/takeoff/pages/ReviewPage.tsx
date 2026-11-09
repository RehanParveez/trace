import { useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../../identity";
import { Badge, EmptyState, ErrorState, LoadingState, TableShell, useToast } from "../../../organizations/components/OrganizationUi";
import { takeoffErrorMessage } from "../utils/errors";
import { ReviewPanel } from "../review/components/ReviewPanel";
import { useReview, useReviewAction } from "../review/hooks/useReview";
import type { ReviewKind } from "../review/types/review.types";
import { countsByKind, KIND_TEXT, KINDS, moneyText, SOURCE_TEXT, SOURCE_TONE, touchedText, visibleRows } from "../review/utils/review";

export function ReviewPage() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { projectId } = useParams<{ projectId: string }>();
  const [search, setSearch] = useSearchParams();
  const item = search.get("item");
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ);
  const canEdit = permissions.includes(IDENTITY_PERMISSIONS.BOQ_UPDATE);
  const [kind, setKind] = useState<ReviewKind | null>(null);
  const [openOnly, setOpenOnly] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const review = useReview(projectId, item);
  const act = useReviewAction(projectId);
  const rows = review.data?.rows ?? [];
  const shown = useMemo(() => visibleRows(rows, kind, openOnly), [rows, kind, openOnly]);
  const counts = useMemo(() => countsByKind(rows, openOnly), [rows, openOnly]);
  const current = shown.find((r) => r.key === selected) ?? shown[0] ?? null;

  if (!canRead) return <EmptyState icon="alert" title={t("boq.review.noAccess", "No access")} description={t("boq.review.noAccessText", "You cannot read the drawings of this project.")} />;
  if (review.isLoading) return <LoadingState label={t("boq.review.loading", "Loading the review list…")} />;
  if (review.isError || !review.data) return <ErrorState title={t("boq.review.loadError", "The review list could not be loaded")} onRetry={() => void review.refetch()} />;

  const send = (action: "accept" | "correct" | "reject" | "withdraw", value: string | null, reason?: string | null) => {
    if (!current) return;
    act.mutate({ key: current.key, body: { action, value, reason: reason ?? null } }, {
      onSuccess: (done) => showToast({ tone: "success", title: t("boq.review.saved", "Decision saved"), description: touchedText(done.touched) }),
      onError: (e) => showToast({ tone: "error", title: t("boq.review.failed", "The decision was not saved"), description: takeoffErrorMessage(e) }),
    });
  };

  return (
    <div className="space-y-4 p-4" data-testid="review-page">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-[Archivo] text-[20px] font-bold">{t("boq.review.title", "Review")}</h1>
        <Badge tone={review.data.open > 0 ? "gold" : "green"}>{t("boq.review.open", "{{n}} to look at", { n: review.data.open })}</Badge>
        {item ? (
          <button type="button" className="text-[12px] underline" onClick={() => setSearch({})} data-testid="review-clear-item">
            {t("boq.review.onlyItem", "Only rows that change {{item}}. Show all.", { item })}
          </button>
        ) : null}
        <label className="ml-auto flex items-center gap-1.5 text-[12.5px]">
          <input type="checkbox" checked={openOnly} onChange={(e) => setOpenOnly(e.target.checked)} />
          {t("boq.review.openOnly", "Only what still needs a decision")}
        </label>
      </div>
      {!review.data.rates_loaded ? <p className="text-[12px] text-[var(--color-text-muted)]">{t("boq.review.noRates", "No rate is loaded for these items, so the list is ordered by the number of BOQ lines each row changes.")}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button type="button" className={`rounded-full border px-3 py-1 text-[12.5px] ${kind === null ? "border-[var(--color-trace-gold)] font-semibold" : "border-[var(--color-border)]"}`} onClick={() => setKind(null)}>
          {t("boq.review.all", "All")} ({KINDS.reduce((n, k) => n + counts[k], 0)})
        </button>
        {KINDS.map((k) => (
          <button key={k} type="button" className={`rounded-full border px-3 py-1 text-[12.5px] ${kind === k ? "border-[var(--color-trace-gold)] font-semibold" : "border-[var(--color-border)]"}`} onClick={() => setKind(k)}>
            {KIND_TEXT[k]} ({counts[k]})
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <EmptyState icon="info" title={t("boq.review.empty", "Nothing to review")} description={review.data.has_ledger ? t("boq.review.emptyText", "Every flagged reading, AI read, conflict and question here has a decision.") : t("boq.review.noLedger", "Run the first reading of this project to see its questions and flagged readings.")} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <TableShell>
            <table className="w-full min-w-[560px] text-left text-[12.5px]" data-testid="review-table">
              <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-3 py-2">{t("boq.review.colWhat", "What")}</th>
                  <th className="px-3 py-2">{t("boq.review.colSource", "Source")}</th>
                  <th className="px-3 py-2">{t("boq.review.colPage", "Sheet")}</th>
                  <th className="px-3 py-2 text-right">{t("boq.review.colMoney", "Effect")}</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.key} onClick={() => setSelected(r.key)} className={`cursor-pointer border-t border-[var(--color-border)] ${current?.key === r.key ? "bg-[var(--color-surface-muted)]" : ""}`} data-testid={`review-row-${r.key}`}>
                    <td className="px-3 py-2">
                      <div className="font-semibold">{r.item}</div>
                      <div className="text-[11px] text-[var(--color-text-muted)]">{KIND_TEXT[r.kind]}{r.touches.length > 0 ? ` · ${r.touches.length} item(s)` : ""}{r.state === "DECIDED" ? " · decided" : ""}</div>
                    </td>
                    <td className="px-3 py-2"><Badge tone={SOURCE_TONE[r.source]}>{SOURCE_TEXT[r.source]}</Badge></td>
                    <td className="px-3 py-2 font-mono">{r.page ?? "—"}</td>
                    <td className="px-3 py-2 text-right font-mono">{moneyText(r.effect_rs)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
          {current ? <ReviewPanel row={current} canEdit={canEdit} busy={act.isPending} onAct={send} /> : null}
        </div>
      )}
    </div>
  );
}
