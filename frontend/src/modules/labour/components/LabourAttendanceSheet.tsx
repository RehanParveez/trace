import { useEffect, useMemo, useState } from "react";
import {Badge, Button, EmptyState, Field, inputClass, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useAttendanceSheet, useBulkRecordAttendance } from "../hooks";
import { useTranslation } from "react-i18next";
import { todayLocal } from "../../../shared/utils/date";

interface LabourAttendanceSheetProps {
  projectId: string;
  canManage: boolean;
  onDeploy: () => void;
}

export function LabourAttendanceSheet({ projectId, canManage, onDeploy }: LabourAttendanceSheetProps) {
  const { t } = useTranslation();
  const bulkAttendance = useBulkRecordAttendance(projectId);
  const { showToast } = useToast();

  const [date, setDate] = useState(() => todayLocal());
  const sheetQuery = useAttendanceSheet(projectId, date);
  const rows = useMemo(() => sheetQuery.data?.rows ?? [], [sheetQuery.data]);

  const [edits, setEdits] = useState<Record<string, string>>({});
  useEffect(() => {
    setEdits({});
  }, [date, projectId]);

  function shown(row: (typeof rows)[number]): string {
    if (edits[row.deployment_id] !== undefined) return edits[row.deployment_id];
    return row.recorded && row.units_present !== null ? String(Number(row.units_present)) : "";
  }

  function setValue(id: string, value: string) {
    setEdits((current) => ({ ...current, [id]: value }));
  }

  function copyPreviousDay() {
    const next: Record<string, string> = {};
    for (const row of rows) {
      if (!row.recorded && row.suggested_units !== null) next[row.deployment_id] = String(Number(row.suggested_units));
    }
    setEdits((current) => ({ ...next, ...current }));
  }

  function markAllPresent() {
    const next: Record<string, string> = {};
    for (const row of rows) {
      if (row.recorded) continue;
      if (!row.is_headcount) next[row.deployment_id] = "1";
      else if (row.suggested_units !== null) next[row.deployment_id] = String(Number(row.suggested_units));
    }
    setEdits((current) => ({ ...next, ...current }));
  }

  const changedEntries = rows
    .filter((row) => edits[row.deployment_id] !== undefined && edits[row.deployment_id] !== "")
    .map((row) => ({ deployment_id: row.deployment_id, attendance_date: date, units_present: Number(edits[row.deployment_id]) }));
  const hasPrefill = rows.some((row) => !row.recorded && row.suggested_units !== null);
  const recordedCount = rows.filter((row) => row.recorded).length;

  function submit() {
    if (changedEntries.length === 0) {
      showToast({ tone: "info", title: t("labour.attendance.nothingToSaveTitle"), description: t("labour.attendance.nothingToSaveDescription") });
      return;
    }
    bulkAttendance.mutate(changedEntries, {
      onSuccess: (result) => {
        setEdits({});
        showToast({ tone: "success", title: t("labour.attendance.saved", { created: result.created, updated: result.updated }) });
      },
      onError: (error) => showToast({ tone: "error", title: t("labour.attendance.saveErrorTitle"), description: getApiErrorMessage(error, t("common.tryAgain")) }),
    });
  }

  const groups = useMemo(() => {
    const map = new Map<string, typeof rows>();
    for (const row of rows) {
      map.set(row.source_name, [...(map.get(row.source_name) ?? []), row]);
    }
    return Array.from(map.entries());
  }, [rows]);

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("labour.attendance.eyebrow")}
        title={t("labour.attendance.title")}
        description={t("labour.attendance.description")}
        action={canManage ? <Button variant="secondary" size="sm" onClick={onDeploy}>{t("labour.attendance.deploy")}</Button> : null}
      />

      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <Field label={t("labour.attendance.date")}>
            <input type="date" max={todayLocal()} className={`${inputClass} max-w-[200px]`} value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          {canManage && rows.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="ghost" size="sm" disabled={!hasPrefill} onClick={copyPreviousDay}>{t("labour.attendance.copyPrevious")}</Button>
              <Button variant="ghost" size="sm" onClick={markAllPresent}>{t("labour.attendance.allPresent")}</Button>
            </div>
          ) : null}
        </div>

        {rows.length > 0 ? (
          <p className="mt-3 text-[12px] text-[var(--color-text-secondary)]">
            {t("labour.attendance.recordedSummary", { recorded: recordedCount, total: rows.length })}
          </p>
        ) : null}

        {sheetQuery.isLoading ? null : rows.length === 0 ? (
          <div className="mt-4">
            <EmptyState icon="users" title={t("labour.attendance.noDeploymentsTitle")} description={t("labour.attendance.noDeploymentsDescription")} />
          </div>
        ) : (
          <div className="mt-4 space-y-5">
            {groups.map(([sourceName, groupRows]) => (
              <div key={sourceName} className="space-y-2">
                <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{sourceName}</div>
                {groupRows.map((row) => (
                  <div key={row.deployment_id} className="flex items-center justify-between gap-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5">
                    <span className="min-w-0 text-[13px] font-medium text-[var(--color-text-primary)]">
                      {row.worker_name ?? row.trade}
                      {row.worker_name ? <span className="ml-1 text-[var(--color-text-secondary)]">· {row.trade}</span> : <span className="ml-1 text-[var(--color-text-secondary)]">{t("labour.attendance.headcountSuffix")}</span>}
                      <span className="ml-1 text-[12px] text-[var(--color-text-secondary)]">— {t("labour.attendance.ratePerDay", { rate: row.daily_rate })}</span>
                      {row.recorded && edits[row.deployment_id] === undefined ? <span className="ml-2"><Badge tone="green">{t("labour.attendance.recordedBadge")}</Badge></span> : null}
                    </span>
                    <input
                      type="number"
                      step={row.is_headcount ? "1" : "0.5"}
                      min="0"
                      max={row.is_headcount ? undefined : "1"}
                      placeholder={row.suggested_units !== null ? String(Number(row.suggested_units)) : ""}
                      className="w-24 shrink-0 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-right text-[13px] outline-none focus:border-[var(--color-trace-gold-dark)]"
                      value={shown(row)}
                      onChange={(e) => setValue(row.deployment_id, e.target.value)}
                      disabled={!canManage}
                    />
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {canManage && rows.length > 0 ? (
          <div className="mt-5 flex justify-end border-t border-[var(--color-border)] pt-4">
            <Button variant="primary" disabled={bulkAttendance.isPending || changedEntries.length === 0} onClick={submit}>
              {bulkAttendance.isPending ? t("common.saving") : t("labour.attendance.save")}
            </Button>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}