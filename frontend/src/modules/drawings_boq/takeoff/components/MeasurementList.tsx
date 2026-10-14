import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState } from "../../../organizations/components/OrganizationUi";
import { isLowConfidence } from "../../utils/drawings-boq.utils";
import type { TakeoffMeasurement } from "../types/takeoff.types";
import { fmtDecimal, fmtPct } from "../utils/format";
import { colourFor } from "../utils/paint";

interface Props {
  measurements: TakeoffMeasurement[];
  selectedIds: string[];
  canEdit: boolean;
  busy: boolean;
  onSelect: (ids: string[]) => void;
  onFocus: (id: string) => void;
  onConfirm: (id: string) => void;
  onUnconfirm: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (m: TakeoffMeasurement) => void;
  onBulkConfirm: (ids: string[]) => void;
  failures: Record<string, string>;
}

const SOURCE_TEXT: Record<string, string> = { MANUAL: "By hand", VECTOR_SNAP: "Snapped", TAG_SCAN: "Tag scan", PRINTED: "Printed" };

export function MeasurementList(p: Props) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<"ALL" | "DRAFT" | "CONFIRMED">("ALL");
  const rows = useMemo(() => p.measurements.filter((m) => filter === "ALL" || m.status === filter), [p.measurements, filter]);
  const drafts = p.measurements.filter((m) => m.status === "DRAFT");
  const selectedDrafts = p.selectedIds.filter((id) => drafts.some((d) => d.id === id));

  if (p.measurements.length === 0) {
    return <EmptyState icon="info" title={t("boq.takeoff.list.emptyTitle", "Nothing measured on this sheet")} description={t("boq.takeoff.list.emptyDesc", "Draw a length, area or count, or pick a wall or room. It appears here as a draft.")} />;
  }
  return (
    <div className="space-y-3 p-4" data-testid="measurement-list">
      <div className="flex flex-wrap items-center gap-2">
        {(["ALL", "DRAFT", "CONFIRMED"] as const).map((f) => (
          <button key={f} type="button" onClick={() => setFilter(f)} className={`rounded-[7px] border px-2.5 py-1 text-[12px] font-semibold ${filter === f ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`}>
            {f === "ALL" ? t("boq.takeoff.list.all", "All") : f === "DRAFT" ? t("boq.takeoff.list.drafts", "Drafts") : t("boq.takeoff.list.confirmed", "Confirmed")}
            {" "}({f === "ALL" ? p.measurements.length : p.measurements.filter((m) => m.status === f).length})
          </button>
        ))}
        {p.canEdit && drafts.length > 0 ? (
          <Button size="sm" className="ml-auto" disabled={p.busy} onClick={() => p.onBulkConfirm(selectedDrafts.length ? selectedDrafts : drafts.map((d) => d.id))} data-testid="bulk-confirm">
            {selectedDrafts.length ? t("boq.takeoff.list.confirmSelected", "Confirm selected ({{n}})", { n: selectedDrafts.length }) : t("boq.takeoff.list.confirmAll", "Confirm all drafts ({{n}})", { n: drafts.length })}
          </Button>
        ) : null}
      </div>
      <ul className="space-y-2">
        {rows.map((m) => {
          const c = m.computed;
          const selected = p.selectedIds.includes(m.id);
          const failure = p.failures[m.id];
          return (
            <li key={m.id} className={`rounded-[8px] border p-2.5 ${selected ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`} data-testid="measurement-row" data-status={m.status}>
              <div className="flex items-start gap-2">
                <input type="checkbox" className="mt-1" checked={selected} onChange={() => p.onSelect(selected ? p.selectedIds.filter((x) => x !== m.id) : [...p.selectedIds, m.id])} aria-label="Select" />
                <span className="mt-1 h-3 w-3 shrink-0 rounded-full" style={{ background: colourFor(m.work_item_code ?? m.kind) }} />
                <button type="button" className="min-w-0 flex-1 text-left" onClick={() => p.onFocus(m.id)}>
                  <div className="truncate text-[13px] font-semibold text-[var(--color-text-primary)]">{m.label || m.tag || `${m.kind.toLowerCase()} ${m.id.slice(0, 4)}`}</div>
                  <div className="truncate text-[11.5px] text-[var(--color-text-muted)]">{m.work_item_code ?? t("boq.takeoff.list.noWorkItem", "no work item")} · {SOURCE_TEXT[m.source] ?? m.source} · {m.recon_mode}</div>
                </button>
                <div className="text-right">
                  {c && !c.error ? (
                    <>
                      <div className="font-mono text-[13px] font-semibold" data-testid="row-quantity">{fmtDecimal(c.quantity, 3)} {c.unit}</div>
                      <div className={`text-[11px] ${isLowConfidence(c.confidence) ? "text-[var(--color-warning)]" : "text-[var(--color-text-muted)]"}`}>{fmtPct(c.confidence)}</div>
                    </>
                  ) : (
                    <div className="max-w-[120px] text-[11px] text-[var(--color-danger)]">{c?.error?.message ?? "—"}</div>
                  )}
                </div>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <Badge tone={m.status === "CONFIRMED" ? "green" : "gold"}>{m.status === "CONFIRMED" ? t("boq.takeoff.list.statusConfirmed", "Confirmed") : t("boq.takeoff.list.statusDraft", "Draft")}</Badge>
                {(c?.warnings ?? []).map((w) => (<Badge key={w} tone="slate">{w}</Badge>))}
                {p.canEdit ? (
                  <span className="ml-auto flex gap-2 text-[12px] font-semibold">
                    {m.status === "DRAFT" ? <button type="button" className="text-[var(--color-success)]" disabled={p.busy} onClick={() => p.onConfirm(m.id)} data-testid="row-confirm">{t("boq.takeoff.list.confirm", "Confirm")}</button> : <button type="button" className="text-[var(--color-warning)]" disabled={p.busy} onClick={() => p.onUnconfirm(m.id)}>{t("boq.takeoff.list.unconfirm", "Back to draft")}</button>}
                    <button type="button" className="text-[var(--color-info)]" onClick={() => p.onEdit(m)}>{t("boq.takeoff.list.edit", "Edit")}</button>
                    <button type="button" className="text-[var(--color-danger)]" disabled={p.busy} onClick={() => p.onDelete(m.id)}>{t("boq.takeoff.list.delete", "Delete")}</button>
                  </span>
                ) : null}
              </div>
              {failure ? <div className="mt-1.5 rounded-[6px] bg-[var(--color-danger-bg)] px-2 py-1 text-[12px] text-[var(--color-danger)]" data-testid="row-failure">{failure}</div> : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
