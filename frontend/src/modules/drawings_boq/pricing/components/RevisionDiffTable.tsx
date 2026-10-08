import { Fragment, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, TableShell } from "../../../organizations/components/OrganizationUi";
import { formatCurrency, formatQuantity } from "../../utils/drawings-boq.utils";
import type { DiffElementRef, DiffLine, DiffStatus } from "../types/pricing.types";
import { DIFF_STATUS_LABEL, deltaClass, diffStatusTone, formatSigned } from "../utils/pricing.utils";

const FILTERS: Array<DiffStatus | "ALL"> = ["ALL", "CHANGED", "ADDED", "REMOVED", "UNCHANGED"];

function ElementList({ title, elements, total }: { title: string; elements: DiffElementRef[]; total: number }) {
  const { t } = useTranslation();
  if (elements.length === 0) return null;
  return (
    <div className="min-w-[220px]">
      <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{title}</div>
      <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
        {elements.map((el) => (
          <li key={el.element_id}>
            {el.name ?? t("pricing.diff.unnamed", "Unnamed element")}
            {el.ifc_global_id ? <span className="ml-1.5 font-mono text-[10.5px] text-[var(--color-text-muted)]">{el.ifc_global_id}</span> : null}
          </li>
        ))}
      </ul>
      {total > elements.length ? (
        <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">
          {t("pricing.diff.andMore", "and {{n}} more", { n: total - elements.length })}
        </div>
      ) : null}
    </div>
  );
}

export function RevisionDiffTable({ lines }: { lines: DiffLine[] }) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<DiffStatus | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<Set<string>>(new Set());

  const counts = useMemo(() => {
    const result: Record<string, number> = { ALL: lines.length };
    for (const line of lines) result[line.status] = (result[line.status] ?? 0) + 1;
    return result;
  }, [lines]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return lines.filter((line) => {
      if (filter !== "ALL" && line.status !== filter) return false;
      if (!needle) return true;
      return `${line.work_item_code ?? ""} ${line.material_name ?? ""}`.toLowerCase().includes(needle);
    });
  }, [lines, filter, search]);

  function toggle(key: string) {
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--color-border)] p-4">
        {FILTERS.filter((f) => f === "ALL" || (counts[f] ?? 0) > 0).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${
              filter === f
                ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
                : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]"
            }`}
          >
            {f === "ALL" ? t("pricing.diff.all", "All") : t(`pricing.diffStatus.${f}`, DIFF_STATUS_LABEL[f])} ({counts[f] ?? 0})
          </button>
        ))}
        <input
          className="ml-auto w-56 rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[12px]"
          value={search}
          placeholder={t("pricing.diff.search", "Search work item or name")}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {visible.length === 0 ? (
        <EmptyState
          icon="check"
          title={t("pricing.diff.emptyTitle", "Nothing to show")}
          description={lines.length === 0 ? t("pricing.diff.noDifferences", "The two versions have no differences.") : t("pricing.diff.noMatch", "No lines match the filter.")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[980px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("pricing.diff.colItem", "Line")}</th>
                <th className="px-4 py-3">{t("pricing.diff.colStatus", "Change")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.diff.colQty", "Quantity (was → now)")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.diff.colRate", "Rate (was → now)")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.diff.colAmount", "Amount change")}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {visible.map((line) => {
                const hasElements = line.elements_added.length > 0 || line.elements_removed.length > 0;
                const expanded = open.has(line.item_key);
                const unit = line.unit_b ?? line.unit_a ?? "";
                return (
                  <Fragment key={line.item_key}>
                    <tr className="border-t border-[var(--color-border)] align-top">
                      <td className="px-4 py-3">
                        <div className="text-[13px] font-semibold">{line.material_name ?? "—"}</div>
                        <div className="font-mono text-[11px] text-[var(--color-text-muted)]">{line.work_item_code ?? "—"}</div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={diffStatusTone(line.status)}>{t(`pricing.diffStatus.${line.status}`, DIFF_STATUS_LABEL[line.status])}</Badge>
                        {line.unit_changed ? (
                          <div className="mt-1 text-[11px] text-[var(--color-warning)]">
                            {t("pricing.diff.unitChanged", "Unit {{a}} → {{b}}", { a: line.unit_a, b: line.unit_b })}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[12.5px]">
                        <div>
                          {line.quantity_a !== null ? formatQuantity(line.quantity_a) : "—"} → {line.quantity_b !== null ? formatQuantity(line.quantity_b) : "—"} {unit}
                        </div>
                        {line.quantity_delta !== null ? (
                          <div className={deltaClass(line.quantity_delta)}>
                            {formatSigned(line.quantity_delta, 2)}
                            {line.quantity_delta_pct !== null ? ` (${formatSigned(line.quantity_delta_pct, 1)}%)` : ""}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[12.5px]">
                        <div>
                          {line.rate_a !== null ? formatCurrency(line.rate_a) : "—"} → {line.rate_b !== null ? formatCurrency(line.rate_b) : "—"}
                        </div>
                        {line.rate_delta !== null && Number(line.rate_delta) !== 0 ? (
                          <div className={deltaClass(line.rate_delta)}>{formatSigned(line.rate_delta, 2)}</div>
                        ) : null}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono text-[12.5px] font-semibold ${deltaClass(line.amount_delta)}`}>
                        {line.amount_delta !== null ? formatSigned(line.amount_delta, 2) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {hasElements ? (
                          <Button variant="ghost" size="sm" onClick={() => toggle(line.item_key)} aria-expanded={expanded}>
                            {expanded ? t("pricing.diff.hideElements", "Hide elements") : t("pricing.diff.showElements", "Elements")}
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                    {expanded ? (
                      <tr className="bg-[var(--color-surface-muted)]">
                        <td colSpan={6} className="px-4 py-3">
                          <div className="flex flex-wrap gap-x-10 gap-y-3">
                            <ElementList title={t("pricing.diff.elementsAdded", "Elements added")} elements={line.elements_added} total={line.element_counts.added ?? line.elements_added.length} />
                            <ElementList title={t("pricing.diff.elementsRemoved", "Elements removed")} elements={line.elements_removed} total={line.element_counts.removed ?? line.elements_removed.length} />
                          </div>
                          {line.element_counts.a !== undefined ? (
                            <div className="mt-2 text-[11.5px] text-[var(--color-text-muted)]">
                              {t("pricing.diff.elementTotals", "{{a}} elements before, {{b}} now", {
                                a: line.element_counts.a, b: line.element_counts.b ?? 0,
                              })}
                            </div>
                          ) : null}
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      )}
    </div>
  );
}
