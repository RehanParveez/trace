import { Fragment, useState } from "react";
import { Badge, Button, EmptyState, TableShell } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useFinishPreview } from "../hooks/useSpacesSchedules";
import { fmt, warningInfo } from "../utils/drawings-boq.utils";
import { useTranslation } from "react-i18next";
import { TraceSteps } from "./TraceSteps";

const th = "px-3 py-2.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function SpaceFinishPreview({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [code, setCode] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [openRow, setOpenRow] = useState<number | null>(null);
  const query = useFinishPreview(spaceId, submitted ?? "", submitted !== null);
  const data = query.data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[200px]">
          <div className="mb-1 text-[11px] font-semibold text-[var(--color-text-muted)]">{t("spaces.preview.ruleSet", "Rule set code (optional)")}</div>
          <input className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12.5px]" value={code} onChange={(e) => setCode(e.target.value)} placeholder="PUNJAB_CSR" />
        </div>
        <Button variant="primary" size="sm" disabled={query.isFetching} onClick={() => { setSubmitted(code.trim()); if (code.trim() === submitted) void query.refetch(); }}>
          {query.isFetching ? t("spaces.preview.running", "Measuring…") : t("spaces.preview.run", "Preview finishes")}
        </Button>
      </div>

      {submitted === null ? (
        <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("spaces.preview.hint", "See what the engine would measure for this room, without running a full calculation.")}</p>
      ) : query.isError ? (
        <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{getApiErrorMessage(query.error, t("spaces.preview.error", "Couldn't preview this room."))}</div>
      ) : !data ? null : (
        <>
          <div className="text-[12px] text-[var(--color-text-muted)]">{t("spaces.preview.usingRules", "Using rule set")} <span className="font-mono">{data.rule_set_code}</span></div>

          <div>
            <div className="mb-1.5 text-[12px] font-semibold text-[var(--color-text-primary)]">{t("spaces.preview.resolved", "Finishes applied")}</div>
            {data.resolved.length === 0 ? (
              <EmptyState icon="info" title={t("spaces.preview.noneResolved", "No finishes apply")} description={t("spaces.preview.noneResolvedDesc", "Add a finish to this room or define a default in the rule set.")} />
            ) : (
              <TableShell>
                <table className="w-full min-w-[520px] text-left">
                  <thead className="bg-[var(--color-surface-muted)]"><tr>
                    <th className={th}>Surface</th><th className={th}>Work item</th><th className={th}>Source</th><th className={`${th} text-right`}>Height mm</th><th className={th}>Deducts openings</th>
                  </tr></thead>
                  <tbody>
                    {data.resolved.map((r, i) => (
                      <tr key={`${r.surface}-${r.work_item_code}-${i}`} className="border-t border-[var(--color-border)]">
                        <td className="px-3 py-2.5 text-[12.5px] font-semibold">{r.surface}</td>
                        <td className="px-3 py-2.5 font-mono text-[12px]">{r.work_item_code}</td>
                        <td className="px-3 py-2.5"><Badge tone={r.source === "MANUAL" ? "blue" : "slate"}>{r.source}</Badge></td>
                        <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">{r.height_mm ?? "—"}</td>
                        <td className="px-3 py-2.5 text-[12px]">{r.deduct_openings ? t("common.yes", "Yes") : t("common.no", "No")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableShell>
            )}
          </div>

          <div>
            <div className="mb-1.5 text-[12px] font-semibold text-[var(--color-text-primary)]">{t("spaces.preview.lines", "Measured quantities")}</div>
            {data.lines.length === 0 ? (
              <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("spaces.preview.noLines", "Nothing was measured.")}</p>
            ) : (
              <TableShell>
                <table className="w-full min-w-[640px] text-left">
                  <thead className="bg-[var(--color-surface-muted)]"><tr>
                    <th className={th}>Surface</th><th className={th}>Work item</th><th className={`${th} text-right`}>Quantity</th><th className={th}>Unit</th><th className={`${th} text-right`}>Confidence</th><th className={th}>Warnings</th><th className={th} />
                  </tr></thead>
                  <tbody>
                    {data.lines.map((l, i) => (
                      <Fragment key={`${l.surface}-${l.work_item_code}-${i}`}>
                        <tr className="border-t border-[var(--color-border)]">
                          <td className="px-3 py-2.5 text-[12.5px] font-semibold">{l.surface || "—"}</td>
                          <td className="px-3 py-2.5 font-mono text-[12px]">{l.work_item_code}</td>
                          <td className="px-3 py-2.5 text-right font-mono text-[13px] font-semibold">{fmt(Number(l.quantity), 4)}</td>
                          <td className="px-3 py-2.5 text-[12px]">{l.unit}</td>
                          <td className={`px-3 py-2.5 text-right font-mono text-[12.5px] ${Number(l.confidence) < 0.6 ? "text-[var(--color-warning)]" : ""}`}>{Math.round(Number(l.confidence) * 100)}%</td>
                          <td className="px-3 py-2.5">
                            <div className="flex flex-wrap gap-1">
                              {l.warnings.map((w) => {
                                const sev = warningInfo(w).severity;
                                return (
                                  <span key={w} title={warningInfo(w).message}>
                                    <Badge tone={sev === "error" ? "red" : sev === "warning" ? "gold" : "slate"}>{w}</Badge>
                                  </span>
                                );
                              })}
                            </div>
                          </td>
                          <td className="px-3 py-2.5 text-right">
                            {l.steps.length > 0 ? <Button variant="ghost" size="sm" onClick={() => setOpenRow(openRow === i ? null : i)}>{openRow === i ? t("spaces.preview.hideSteps", "Hide working") : t("spaces.preview.steps", "Working")}</Button> : null}
                          </td>
                        </tr>
                        {openRow === i ? (
                          <tr className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)]">
                            <td colSpan={7} className="px-4 py-3">
                              <div className="mb-1 font-mono text-[11px] text-[var(--color-text-muted)]">{l.formula_code} · {l.source_kind}</div>
                              <TraceSteps steps={l.steps} />
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </TableShell>
            )}
          </div>

          {Object.keys(data.skipped).length > 0 ? (
            <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2.5">
              <div className="mb-1 text-[11px] font-semibold text-[var(--color-text-muted)]">{t("spaces.preview.skipped", "Skipped")}</div>
              <ul className="space-y-0.5 font-mono text-[11.5px] text-[var(--color-text-secondary)]">
                {Object.entries(data.skipped).map(([k, v]) => <li key={k}>{k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}</li>)}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}