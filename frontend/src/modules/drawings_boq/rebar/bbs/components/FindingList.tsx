import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { REPORT_PAGE_SIZE } from "../api/bbsReport.api";
import { useDecideReportFinding, useFindingCrops, useReportFindings, useSignFinding } from "../hooks/useBbsReport";
import { CLASS_ORDER, classTone, statusTone, whereLabel } from "../utils/bbsAudit";
import { basisLabel, conventionLabel, drawingLabel } from "../utils/bbsCrosscheck";
import { cropSrc, signedKg } from "../utils/bbsReport";
import type { FindingDecision } from "../types/bbsAudit.types";
import type { CropSide, FindingCrops, ReportFilters, ReportFinding, ReportSheet } from "../types/bbsReport.types";
import { FindingActions } from "./FindingActions";

const select = "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px]";
const STATUSES = ["OPEN", "ACCEPTED", "REJECTED", "SIGNED"] as const;

interface EvidenceProps {
  finding: ReportFinding;
  crops: FindingCrops | undefined;
  loading: boolean;
  failed: boolean;
}

function Side({ title, side, fallback }: { title: string; side: CropSide | undefined; fallback: string }) {
  const { t } = useTranslation();
  const src = cropSrc(side);
  return (
    <figure className="min-w-0 flex-1 space-y-1">
      <figcaption className="text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{title}</figcaption>
      {src ? <img src={src} alt={title} className="max-h-[320px] w-full rounded-[6px] border border-[var(--color-border)] bg-white object-contain" /> : (
        <div className="rounded-[6px] border border-dashed border-[var(--color-border)] px-3 py-3 text-[12px] text-[var(--color-text-secondary)]">
          <div className="font-mono">{side?.text || fallback || "—"}</div>
          <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{side?.message ?? t("bbs.crop.none", "No picture")}</div>
        </div>
      )}
    </figure>
  );
}

export function FindingEvidence({ finding, crops, loading, failed }: EvidenceProps) {
  const { t } = useTranslation();
  if (loading) return <LoadingState label={t("bbs.crop.loading", "Cutting the pictures…")} />;
  return (
    <div className="space-y-1" data-testid="finding-evidence">
      {failed ? <p className="text-[11.5px] text-[var(--color-warning)]">{t("bbs.crop.failed", "The pictures could not be loaded. The places are given as text.")}</p> : null}
      <div className="flex flex-col gap-3 md:flex-row">
        <Side title={t("bbs.crop.schedule", "Schedule")} side={crops?.bbs} fallback={whereLabel(finding.bbs_ref)} />
        <Side title={t("bbs.crop.drawing", "Drawing")} side={crops?.drawing} fallback={finding.drawing_ref ? drawingLabel(finding.drawing_ref) : t("bbs.crop.noRef", "No place on the drawings")} />
      </div>
    </div>
  );
}

interface ItemProps {
  documentId: string;
  finding: ReportFinding;
  open: boolean;
  canEdit: boolean;
  onToggle: () => void;
}

function FindingItem({ documentId, finding: f, open, canEdit, onToggle }: ItemProps) {
  const { t } = useTranslation();
  const crops = useFindingCrops(f.id, open);
  const decide = useDecideReportFinding(documentId);
  const sign = useSignFinding(documentId);
  const [error, setError] = useState<string | null>(null);

  function onDecide(status: FindingDecision, reason: string) {
    setError(null);
    decide.mutate({ findingId: f.id, status, reason }, { onError: (e) => setError(getApiErrorMessage(e, t("bbs.decideError", "Couldn't save this decision."))) });
  }

  function onSign(reason: string) {
    setError(null);
    sign.mutate({ findingId: f.id, reason }, { onError: (e) => setError(getApiErrorMessage(e, t("bbs.signError", "Couldn't sign this convention."))) });
  }

  return (
    <li className="rounded-[8px] border border-[var(--color-border)]" data-testid="finding-item">
      <button type="button" className="flex w-full flex-wrap items-center gap-2 px-3 py-2 text-left transition hover:bg-[var(--color-surface-muted)]" aria-expanded={open} onClick={onToggle}>
        <span className="font-mono text-[12px] font-semibold text-[var(--color-text-muted)]">F{f.no}</span>
        <span className="font-mono text-[12px]">{f.code}</span>
        <Badge tone={classTone(f.finding_class)}>{f.finding_class}</Badge>
        <span className="min-w-0 flex-1 truncate text-[12px] text-[var(--color-text-secondary)]">{whereLabel(f.bbs_ref)}</span>
        <span className="font-mono text-[12px]">{signedKg(f.diff_kg)} kg</span>
        <Badge tone={statusTone(f.status)}>{f.status}</Badge>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3">
          <FindingEvidence finding={f} crops={crops.data} loading={crops.isLoading} failed={crops.isError} />
          <div className="grid gap-x-6 gap-y-1 font-mono text-[12px] sm:grid-cols-2">
            <div><span className="text-[var(--color-text-muted)]">{t("bbs.col.bbs", "Schedule")}: </span>{f.bbs_value ?? "—"}</div>
            <div><span className="text-[var(--color-text-muted)]">{t("bbs.col.trace", "Trace")}: </span>{f.trace_value ?? "—"}</div>
          </div>
          <div className="text-[12px] text-[var(--color-text-secondary)]">{f.rule}</div>
          {f.question ? <div className="text-[12px] font-semibold text-[var(--color-warning)]">{f.question}</div> : null}
          <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11.5px] text-[var(--color-text-muted)]">
            {f.effect_basis ? <span>{basisLabel(f)}</span> : null}
            {f.convention ? <span>{conventionLabel(f.convention)}</span> : null}
          </div>
          {f.reason ? <div className="text-[12px] italic text-[var(--color-text-muted)]">{t("bbs.reasonWas", "Reason given")}: {f.reason}</div> : null}
          {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
          {canEdit ? <FindingActions key={`${f.id}-${f.status}`} finding={f} pending={decide.isPending || sign.isPending} onDecide={onDecide} onSign={onSign} /> : null}
        </div>
      ) : null}
    </li>
  );
}

interface FindingListProps {
  documentId: string;
  canEdit: boolean;
  sheets: ReportSheet[];
  filters: ReportFilters;
  onFilters: (next: ReportFilters) => void;
}

export function FindingList({ documentId, canEdit, sheets, filters, onFilters }: FindingListProps) {
  const { t } = useTranslation();
  const query = useReportFindings(documentId, filters);
  const [openId, setOpenId] = useState<string | null>(null);
  const data = query.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / REPORT_PAGE_SIZE)) : 1;
  const firstId = data?.items[0]?.id ?? null;
  const expanded = openId ?? firstId;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] pb-3">
        <select aria-label={t("bbs.filter.class", "Class")} className={select} value={filters.finding_class ?? ""} onChange={(e) => onFilters({ ...filters, finding_class: e.target.value, page: 1 })}>
          <option value="">{t("bbs.filter.allClasses", "All classes")}</option>
          {CLASS_ORDER.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select aria-label={t("bbs.filter.sheet", "Sheet")} className={select} value={filters.sheet ?? ""} onChange={(e) => onFilters({ ...filters, sheet: e.target.value === "" ? null : Number(e.target.value), page: 1 })}>
          <option value="">{t("bbs.filter.allSheets", "All sheets")}</option>
          {sheets.map((s) => <option key={s.idx} value={s.idx}>{s.name}</option>)}
        </select>
        <select aria-label={t("bbs.filter.status", "Status")} className={select} value={filters.status ?? ""} onChange={(e) => onFilters({ ...filters, status: e.target.value, page: 1 })}>
          <option value="">{t("bbs.filter.allStatuses", "All statuses")}</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        {data ? <span className="ml-auto self-center text-[12px] text-[var(--color-text-muted)]">{t("bbs.findings.count", "{{n}} finding(s)", { n: data.total })}</span> : null}
      </div>
      {query.isLoading ? <LoadingState label={t("bbs.findings.loading", "Loading findings…")} /> : query.isError ? (
        <ErrorState title={t("bbs.findings.error", "Couldn't load the findings")} onRetry={() => void query.refetch()} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState icon="info" title={data?.run_id ? t("bbs.findings.none", "No findings match") : t("bbs.findings.notRun", "The audit has not been run")}
          description={data?.run_id ? t("bbs.findings.noneDesc", "Change the filters to see other findings.") : t("bbs.findings.notRunDesc", "Run the audit to check the arithmetic of this schedule.")} />
      ) : (
        <ul className="space-y-2">
          {data.items.map((f) => <FindingItem key={f.id} documentId={documentId} finding={f} open={expanded === f.id} canEdit={canEdit} onToggle={() => setOpenId(expanded === f.id ? "" : f.id)} />)}
        </ul>
      )}
      {data && pages > 1 ? (
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" disabled={filters.page <= 1} onClick={() => onFilters({ ...filters, page: filters.page - 1 })}>{t("bbs.prev", "Previous")}</Button>
          <span className="text-[12px] text-[var(--color-text-muted)]">{filters.page} / {pages}</span>
          <Button variant="ghost" size="sm" disabled={filters.page >= pages} onClick={() => onFilters({ ...filters, page: filters.page + 1 })}>{t("bbs.next", "Next")}</Button>
        </div>
      ) : null}
    </div>
  );
}
