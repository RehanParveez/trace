import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, TableShell } from "../../../../organizations/components/OrganizationUi";
import type { ImportRow } from "../types/schedules.types";
import { FLAG_LABEL, REVIEW_FLAGS, flagTone, formatRate, printedRate, rowStatus } from "../utils/schedules.utils";

interface Props {
  rows: ImportRow[];
  selected: Set<string>;
  canManage: boolean;
  editable: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onToggle: (id: string) => void;
  onToggleAll: (ids: string[], on: boolean) => void;
  onOpen: (row: ImportRow) => void;
  onVerify: (row: ImportRow) => void;
  onLoadMore: () => void;
}

export function ImportRowTable({ rows, selected, canManage, editable, hasMore, loadingMore, onToggle, onToggleAll, onOpen, onVerify, onLoadMore }: Props) {
  const { t } = useTranslation();
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));

  if (rows.length === 0) {
    return <EmptyState icon="budget" title={t("schedules.rows.emptyTitle", "No rows here")} description={t("schedules.rows.emptyDesc", "Nothing matches this filter.")} />;
  }

  return (
    <div>
      <TableShell>
        <table className="w-full min-w-[960px] text-left text-[12.5px]">
          <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            <tr>
              {canManage && editable ? (
                <th className="w-9 px-3 py-2.5">
                  <input type="checkbox" aria-label={t("schedules.rows.selectAll", "Select all shown")} checked={allSelected} onChange={(e) => onToggleAll(rows.map((r) => r.id), e.target.checked)} />
                </th>
              ) : null}
              <th className="px-3 py-2.5">#</th>
              <th className="px-3 py-2.5">{t("schedules.rows.item", "Item")}</th>
              <th className="px-3 py-2.5">{t("schedules.rows.description", "Description")}</th>
              <th className="px-3 py-2.5">{t("schedules.rows.rate", "Rate as printed")}</th>
              <th className="px-3 py-2.5 text-right">{t("schedules.rows.perUnit", "Per unit")}</th>
              <th className="px-3 py-2.5">{t("schedules.rows.mapping", "Work item")}</th>
              <th className="px-3 py-2.5">{t("schedules.rows.state", "State")}</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {rows.map((row) => {
              const state = rowStatus(row);
              const top = row.suggestions[0];
              return (
                <tr key={row.id} className={row.skipped ? "opacity-55" : undefined}>
                  {canManage && editable ? (
                    <td className="px-3 py-2.5 align-top">
                      <input type="checkbox" aria-label={t("schedules.rows.select", "Select row {{n}}", { n: row.seq })} checked={selected.has(row.id)} onChange={() => onToggle(row.id)} />
                    </td>
                  ) : null}
                  <td className="px-3 py-2.5 align-top text-[var(--color-text-muted)]">{row.seq}{row.page ? <span className="block text-[11px]">p{row.page}</span> : null}</td>
                  <td className="px-3 py-2.5 align-top font-mono">{row.item_no ?? "—"}</td>
                  <td className="max-w-[360px] px-3 py-2.5 align-top">
                    <div className="line-clamp-2 text-[var(--color-text-primary)]" title={row.description}>{row.description}</div>
                    {row.chapter ? <div className="mt-0.5 truncate text-[11px] text-[var(--color-text-muted)]">{row.chapter}</div> : null}
                    {row.flags.filter((f) => REVIEW_FLAGS.has(f) || f === "BASIS_APPLIED").length > 0 ? (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {row.flags.filter((f) => REVIEW_FLAGS.has(f) || f === "BASIS_APPLIED").map((f) => (
                          <Badge key={f} tone={flagTone(f)}>{t(`schedules.flag.${f}`, FLAG_LABEL[f] ?? f)}</Badge>
                        ))}
                      </div>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 align-top">{printedRate(row)}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-right align-top font-semibold">{formatRate(row.unit_rate, 2)}</td>
                  <td className="px-3 py-2.5 align-top">
                    {row.work_item_code ? (
                      <div><span className="font-mono font-semibold">{row.work_item_code}</span>{row.mapping_source ? <span className="ml-1 text-[11px] text-[var(--color-text-muted)]">{row.mapping_source === "MANUAL" ? t("schedules.rows.byYou", "you") : row.mapping_source === "CSR_REF" ? t("schedules.rows.byRef", "ref no") : t("schedules.rows.bySuggestion", "suggested")}</span> : null}</div>
                    ) : top ? (
                      <div className="text-[var(--color-text-muted)]" title={top.description}>
                        {t("schedules.rows.maybe", "maybe")} <span className="font-mono">{top.code}</span> {Math.round(top.score * 100)}%
                      </div>
                    ) : <span className="text-[var(--color-text-muted)]">—</span>}
                  </td>
                  <td className="px-3 py-2.5 align-top">
                    <Badge tone={state === "mapped" ? "green" : state === "review" ? "gold" : state === "skipped" ? "slate" : "blue"}>
                      {state === "mapped" ? t("schedules.rows.mapped", "Mapped") : state === "review" ? t("schedules.rows.review", "To review") : state === "skipped" ? t("schedules.rows.skipped", "Left out") : t("schedules.rows.unmapped", "Not mapped")}
                    </Badge>
                    {row.is_sample ? (
                      <div className="mt-1">
                        <Badge tone={row.sample_verified ? "green" : "gold"}>{row.sample_verified ? t("schedules.rows.checked", "Spot-checked") : t("schedules.rows.spot", "Spot-check")}</Badge>
                      </div>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-right align-top">
                    {row.is_sample && !row.sample_verified && canManage && editable ? (
                      <Button size="sm" variant="secondary" onClick={() => onVerify(row)} title={t("schedules.rows.verifyHelp", "Compare this row with the page, then confirm it matches")}>
                        {t("schedules.rows.verify", "Matches page")}
                      </Button>
                    ) : null}{" "}
                    <Button size="sm" variant="ghost" onClick={() => onOpen(row)}>{canManage && editable ? t("schedules.rows.edit", "Open") : t("schedules.rows.view", "View")}</Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableShell>
      {hasMore ? (
        <div className="flex justify-center border-t border-[var(--color-border)] p-3">
          <Button variant="secondary" size="sm" disabled={loadingMore} onClick={onLoadMore}>
            {loadingMore ? t("common.loading", "Loading…") : t("schedules.rows.more", "Show more rows")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
