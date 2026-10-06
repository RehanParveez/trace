import { useState } from "react";
import {Badge, Button, EmptyState, ErrorState, LoadingState, TableShell,
} from "../../organizations/components/OrganizationUi";
import {useRunDeductions, useRunLedger, useRunSolids,
} from "../hooks/useDrawingsBoq";
import {formatPrecise, isLowConfidence, warningInfo,
} from "../utils/drawings-boq.utils";
import type { DeductionKind } from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

const DEDUCTION_TYPES: DeductionKind[] = [
  "OVERLAP_ALLOCATION",
  "EXTENT_TRIMMING",
  "VOID_DEDUCTION",
  "MATERIAL_SUBSTITUTION",
  "MEASUREMENT_CONVENTION",
];

const selectCls =
  "rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12px]";
const th =
  "px-3 py-2.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

type Tab = "solids" | "ledger" | "deductions";

export function RunDetailsPanel({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("ledger");
  const [role, setRole] = useState("");
  const [workItem, setWorkItem] = useState("");
  const [dedType, setDedType] = useState<DeductionKind | "">("");

  const solids = useRunSolids(tab === "solids" ? runId : undefined, {
    role: role || undefined,
  });
  const ledger = useRunLedger(tab === "ledger" ? runId : undefined, {
    work_item_code: workItem || undefined,
  });
  const deductions = useRunDeductions(
    tab === "deductions" ? runId : undefined,
    { deduction_type: dedType || undefined },
  );
  const current =
    tab === "solids" ? solids : tab === "ledger" ? ledger : deductions;

  const tabCls = (active: boolean) =>
    `rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${
      active
        ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]"
        : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"
    }`;

  const tabLabel = (k: Tab) => {
    if (k === "ledger") return t("boq.calculationRun.tabLedger");
    if (k === "solids") return t("boq.calculationRun.tabSolids");
    return t("boq.calculationRun.tabDeductions");
  };

  const loadingLabel =
    tab === "solids"
      ? t("boq.calculationRun.solidsLoading")
      : tab === "ledger"
        ? t("boq.calculationRun.ledgerLoading")
        : t("boq.calculationRun.deductionsLoading");

  const errorTitle =
    tab === "solids"
      ? t("boq.calculationRun.solidsLoadError")
      : tab === "ledger"
        ? t("boq.calculationRun.ledgerLoadError")
        : t("boq.calculationRun.deductionsLoadError");

  return (
    <div className="border-t border-[var(--color-border)]">
      <div className="flex flex-wrap items-center gap-2 p-4">
        {(["ledger", "solids", "deductions"] as Tab[]).map((k) => (
          <button
            key={k}
            type="button"
            className={tabCls(tab === k)}
            onClick={() => setTab(k)}
          >
            {tabLabel(k)}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2">
          {tab === "solids" ? (
            <input
              className={selectCls}
              placeholder={t("boq.calculationRun.filterRole", "Role, e.g. WALL")}
              value={role}
              onChange={(e) => setRole(e.target.value.toUpperCase())}
            />
          ) : null}

          {tab === "ledger" ? (
            <input
              className={selectCls}
              placeholder={t(
                "boq.calculationRun.filterWorkItem",
                "Work item code",
              )}
              value={workItem}
              onChange={(e) => setWorkItem(e.target.value)}
            />
          ) : null}

          {tab === "deductions" ? (
            <select
              className={selectCls}
              value={dedType}
              onChange={(e) =>
                setDedType(e.target.value as DeductionKind | "")
              }
            >
              <option value="">
                {t("boq.calculationRun.allTypes", "All types")}
              </option>
              {DEDUCTION_TYPES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          ) : null}
        </div>
      </div>

      {current.isLoading ? (
        <LoadingState label={loadingLabel} />
      ) : current.isError ? (
        <ErrorState
          title={errorTitle}
          onRetry={() => void current.refetch()}
        />
      ) : current.rows.length === 0 ? (
        <EmptyState
          icon="info"
          title={t("boq.calculationRun.noRowsFound")}
          description={t(
            "boq.calculationRun.noRowsDesc",
            "Nothing matches this filter.",
          )}
        />
      ) : (
        <TableShell>
          {tab === "solids" ? (
            <table className="w-full min-w-[820px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr>
                  <th className={th}>
                    {t("boq.calculationRun.colRole")}
                  </th>
                  <th className={th}>
                    {t("boq.calculationRun.colComponent")}
                  </th>
                  <th className={th}>
                    {t("boq.calculationRun.colGeometry")}
                  </th>
                  <th className={`${th} text-right`}>
                    {t("boq.calculationRun.colVolumeM3")}
                  </th>
                  <th className={`${th} text-right`}>
                    {t("boq.calculationRun.colAreaM2")}
                  </th>
                  <th className={`${th} text-right`}>
                    {t("boq.calculationRun.colLengthM")}
                  </th>
                  <th className={`${th} text-right`}>Count</th>
                  <th className={th}>
                    {t("boq.calculationRun.colStatus")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {solids.rows.map((s) => (
                  <tr
                    key={s.id}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-3 py-2.5 text-[12.5px] font-semibold">
                      {s.role}
                    </td>
                    <td className="px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
                      {s.component_type}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[11.5px]">
                      {s.geometry_kind}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {formatPrecise(s.gross_volume_m3, 6)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {formatPrecise(s.gross_area_m2, 6)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {formatPrecise(s.gross_length_m, 6)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {s.count ?? "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <Badge
                        tone={
                          s.status === "OK"
                            ? "green"
                            : s.status === "REJECTED"
                              ? "red"
                              : "gold"
                        }
                      >
                        {s.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : tab === "ledger" ? (
            <table className="w-full min-w-[820px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr>
                  <th className={th}>
                    {t("boq.ledger.colWorkItem")}
                  </th>
                  <th className={`${th} text-right`}>
                    {t("boq.ledger.colQuantity")}
                  </th>
                  <th className={th}>{t("boq.ledger.colUnit")}</th>
                  <th className={th}>Grade</th>
                  <th className={th}>{t("boq.ledger.colFormula")}</th>
                  <th className={`${th} text-right`}>
                    {t("boq.ledger.colConfidence")}
                  </th>
                  <th className={th}>Warnings</th>
                </tr>
              </thead>
              <tbody>
                {ledger.rows.map((l) => (
                  <tr
                    key={l.id}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-3 py-2.5 font-mono text-[12.5px] font-semibold">
                      {l.work_item_code}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {formatPrecise(l.quantity_net, 6)}
                    </td>
                    <td className="px-3 py-2.5 text-[12px]">{l.unit}</td>
                    <td className="px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
                      {l.material_grade ?? "—"}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[11.5px] text-[var(--color-text-secondary)]">
                      {l.formula_code}
                    </td>
                    <td
                      className={`px-3 py-2.5 text-right font-mono text-[12.5px] ${
                        isLowConfidence(l.confidence)
                          ? "text-[var(--color-warning)]"
                          : ""
                      }`}
                    >
                      {Math.round(Number(l.confidence) * 100)}%
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {l.warnings.map((w) => (
                          <span key={w} title={warningInfo(w).message}>
                            <Badge
                              tone={
                                warningInfo(w).severity === "error"
                                  ? "red"
                                  : warningInfo(w).severity === "warning"
                                    ? "gold"
                                    : "slate"
                              }
                            >
                              {w}
                            </Badge>
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className="w-full min-w-[820px] text-left">
              <thead className="bg-[var(--color-surface-muted)]">
                <tr>
                  <th className={th}>
                    {t("boq.calculationRun.colType")}
                  </th>
                  <th className={`${th} text-right`}>
                    {t("boq.calculationRun.colQuantity")}
                  </th>
                  <th className={th}>
                    {t("boq.calculationRun.colUnit")}
                  </th>
                  <th className={th}>
                    {t("boq.calculationRun.colRule")}
                  </th>
                  <th className={th}>
                    {t("boq.calculationRun.colExplanation")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {deductions.rows.map((d) => (
                  <tr
                    key={d.id}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-3 py-2.5 font-mono text-[11.5px] font-semibold">
                      {d.deduction_type}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[12.5px]">
                      {formatPrecise(d.quantity, 6)}
                    </td>
                    <td className="px-3 py-2.5 text-[12px]">{d.unit}</td>
                    <td className="px-3 py-2.5 font-mono text-[11.5px] text-[var(--color-text-secondary)]">
                      {d.rule_code}
                      {d.rule_version ? ` v${d.rule_version}` : ""}
                    </td>
                    <td className="px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">
                      {d.explanation ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </TableShell>
      )}

      {current.hasNextPage ? (
        <div className="flex justify-center border-t border-[var(--color-border)] p-3">
          <Button
            variant="ghost"
            size="sm"
            disabled={current.isFetchingNextPage}
            onClick={() => void current.fetchNextPage()}
          >
            {current.isFetchingNextPage
              ? t("common.loading")
              : t("boq.calculationRun.loadMore")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}