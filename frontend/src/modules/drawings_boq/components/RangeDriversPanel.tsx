import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, LoadingState, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useBOQRangeDrivers } from "../hooks";
import type { RangeDriver, RangeDriverItem, RangeDriversUnit, RangeOpenInput } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { useGradeLabel } from "../utils/gradeLabel";
import { gradeTone } from "../utils/quantityRange";
import { staleOf } from "../utils/driverMarks";
import { ConfirmFirstTable, MarkList, OpenMarks } from "./DriverMarks";

const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";

const INPUT_TEXT: Record<string, string> = {
  count: "Count",
  size: "Size",
  length: "Length",
  thickness: "Thickness",
  height: "Height",
  depth: "Depth",
  area: "Area",
  width: "Width",
  section: "Section",
  projections: "Projections",
  openings: "Openings",
  landings: "Landings",
  slabs: "Slabs",
  piers: "Piers",
  "waist slab": "Waist slab",
};

function useInputLabel(): (name: string) => string {
  const { t } = useTranslation();
  return (name: string) => {
    if (name === "(not itemised)") return t("boq.drivers.notItemised", "Not itemised (older run)");
    const key = name.trim().toLowerCase();
    return t(`boq.drivers.input.${key.replace(/\s+/g, "_")}`, INPUT_TEXT[key] ?? name);
  };
}

function Items({ items }: { items: RangeDriverItem[] }) {
  if (items.length === 0) return null;
  return (
    <span className="text-[var(--color-text-muted)]">
      {items
        .slice(0, 3)
        .map((i) => i.name ?? "—")
        .join(" · ")}
    </span>
  );
}

function DriverRow({ driver, unit }: { driver: RangeDriver; unit: string }) {
  const { t } = useTranslation();
  const gradeLabel = useGradeLabel();
  const inputLabel = useInputLabel();
  return (
    <tr className="border-t border-[var(--color-border)] align-top" data-testid={`driver-${driver.name}-${driver.basis}`}>
      <td className="px-3 py-1.5 font-semibold text-[var(--color-text-primary)]">{inputLabel(driver.name)}</td>
      <td className="px-3 py-1.5">
        <Badge tone={gradeTone(driver.basis)}>{gradeLabel(driver.basis)}</Badge>
      </td>
      <td className="px-3 py-1.5">
        <div className="flex items-center gap-2">
          <div className="h-2 w-24 rounded-full bg-[var(--color-surface-muted)]" aria-hidden="true">
            <div className="h-2 rounded-full bg-[var(--color-primary)]" style={{ width: `${Math.min(100, Math.max(0, driver.share_pct))}%` }} />
          </div>
          <span className="font-mono">{driver.share_pct.toFixed(1)}%</span>
        </div>
      </td>
      <td className="px-3 py-1.5 text-right font-mono">
        −{formatPrecise(driver.swing_down, 3)} / +{formatPrecise(driver.swing_up, 3)} {unit}
      </td>
      <td className="px-3 py-1.5 text-right font-mono" title={t("boq.drivers.afterHint", "The range of the whole {{unit}} total if this input were confirmed", { unit })}>
        {formatPrecise(driver.low_after, 3)} – {formatPrecise(driver.high_after, 3)}
      </td>
      <td className="px-3 py-1.5 text-[11.5px]">
        <div>{t("boq.drivers.rowsItems", "{{rows}} rows in {{items}} items", { rows: driver.rows, items: driver.items })}</div>
        <Items items={driver.top_items} />
        <MarkList marks={driver.marks} />
      </td>
    </tr>
  );
}

function OpenRow({ open, unit }: { open: RangeOpenInput; unit: string }) {
  const { t } = useTranslation();
  const inputLabel = useInputLabel();
  return (
    <li className="rounded-[6px] border border-[var(--color-border)] px-3 py-2" data-testid={`open-input-${open.name}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-[var(--color-text-primary)]">{inputLabel(open.name)}</span>
        <Badge tone="red">{t("boq.drivers.missing", "missing")}</Badge>
        <span className="font-mono">
          {formatPrecise(open.quantity, 3)} {unit}
        </span>
        {open.share_of_quantity_pct !== null ? (
          <span className="text-[var(--color-text-muted)]">{t("boq.drivers.ofTotal", "{{pct}}% of the total", { pct: open.share_of_quantity_pct.toFixed(1) })}</span>
        ) : null}
        <span className="text-[var(--color-text-muted)]">{t("boq.drivers.rowsItems", "{{rows}} rows in {{items}} items", { rows: open.rows, items: open.items })}</span>
      </div>
      <div className="mt-0.5 text-[11.5px]">
        <Items items={open.top_items} />
        <MarkList marks={open.marks} />
      </div>
    </li>
  );
}

function UnitBlock({ unit }: { unit: RangeDriversUnit }) {
  const { t } = useTranslation();
  const inputTotal = unit.drivers.length + unit.open_inputs.length;
  return (
    <section className="border-b border-[var(--color-border)] px-5 py-4" data-testid={`drivers-unit-${unit.unit}`}>
      <div className="flex flex-wrap items-baseline gap-3">
        <h3 className="text-[13px] font-bold text-[var(--color-text-primary)]">{unit.unit || "—"}</h3>
        <span className="font-mono text-[12px]">
          {formatPrecise(unit.likely, 3)} <span className="text-[var(--color-text-muted)]">({formatPrecise(unit.low, 3)} – {formatPrecise(unit.high, 3)})</span>
        </span>
        <span className="text-[11.5px] text-[var(--color-text-muted)]">
          {t("boq.drivers.rowCounts", "{{bounded}} of {{rows}} rows have a range", { bounded: unit.bounded_rows, rows: unit.rows })}
        </span>
      </div>
      <ConfirmFirstTable work={unit.confirm_first} unit={unit.unit} />
      <OpenMarks work={unit.open_marks} unit={unit.unit} />
      {unit.open_inputs.length > 0 ? (
        <div className="mt-3">
          <div className={HEAD}>{t("boq.drivers.openTitle", "Not found on the drawing: these rows have no range yet")}</div>
          <ul className="mt-1 list-none space-y-1.5 pl-0 text-[12px]">
            {unit.open_inputs.map((o) => (
              <OpenRow key={o.name} open={o} unit={unit.unit} />
            ))}
          </ul>
        </div>
      ) : null}
      {unit.drivers.length > 0 ? (
        <div className="mt-3">
          <div className={HEAD}>{t("boq.drivers.confirmTitle", "Confirm these first: the inputs that move this total most")}</div>
          <div className="mt-1 overflow-x-auto rounded-[8px] border border-[var(--color-border)]">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-[var(--color-surface-muted)] text-left">
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.drivers.colInput", "Input")}</th>
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.drivers.colBasis", "Found by")}</th>
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.drivers.colShare", "Share of the spread")}</th>
                  <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.drivers.colSwing", "Swing")}</th>
                  <th className={`${HEAD} px-3 py-2 text-right`}>{t("boq.drivers.colAfter", "Total range if confirmed")}</th>
                  <th className={`${HEAD} px-3 py-2`}>{t("boq.drivers.colWhere", "Where")}</th>
                </tr>
              </thead>
              <tbody>
                {unit.drivers.map((d) => (
                  <DriverRow key={`${d.name}|${d.basis}`} driver={d} unit={unit.unit} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {inputTotal === 0 ? <p className="mt-2 text-[12px] text-[var(--color-text-secondary)]">{t("boq.drivers.none", "Nothing here is uncertain: every input is printed or confirmed.")}</p> : null}
      {unit.no_range_rows > 0 || unit.leaves_out_rows > 0 ? (
        <p className="mt-2 text-[11.5px] text-[var(--color-warning)]">
          {unit.no_range_rows > 0 ? t("boq.drivers.noRange", "{{n}} rows were never graded.", { n: unit.no_range_rows }) : null}{" "}
          {unit.leaves_out_rows > 0 ? t("boq.drivers.leavesOut", "{{n}} rows leave something out, so the total is a minimum.", { n: unit.leaves_out_rows }) : null}
        </p>
      ) : null}
    </section>
  );
}

export function RangeDriversPanel({ versionId }: { versionId: string }) {
  const { t } = useTranslation();
  const q = useBOQRangeDrivers(versionId);
  const stale = staleOf(q.data);
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.drivers.eyebrow", "WHAT TO CONFIRM FIRST")}
        title={t("boq.drivers.title", "Which unknowns move the bill most")}
        description={t(
          "boq.drivers.description",
          "Every quantity's spread comes from the inputs behind it. Here they are added up across the bill, biggest first, with the range the total would have if that one input were confirmed.",
        )}
      />
      {q.isLoading ? (
        <LoadingState label={t("boq.drivers.loading", "Working out what moves the bill…")} />
      ) : q.isError ? (
        <ErrorState title={t("boq.drivers.loadError", "The list of unknowns could not be loaded.")} onRetry={() => void q.refetch()} />
      ) : !q.data || q.data.units.length === 0 ? (
        <EmptyState icon="building" title={t("boq.drivers.empty", "There are no graded quantities to rank yet.")} description="" />
      ) : (
        <div data-testid="range-drivers">
          {stale ? (
            <p className="border-b border-[var(--color-border)] bg-[var(--color-warning-bg)] px-5 py-2 text-[12px] text-[var(--color-warning)]" data-testid="drivers-stale">
              {t("boq.marks.stale", "{{n}} of the marks below were changed after this run ({{reopened}} reopened, {{changed}} re-confirmed, {{gone}} deleted). Run the bill again to see their effect.", {
                n: stale.reopened + stale.changed + stale.gone,
                reopened: stale.reopened,
                changed: stale.changed,
                gone: stale.gone,
              })}
            </p>
          ) : null}
          {q.data.units.map((u) => (
            <UnitBlock key={u.unit} unit={u} />
          ))}
        </div>
      )}
    </Panel>
  );
}
