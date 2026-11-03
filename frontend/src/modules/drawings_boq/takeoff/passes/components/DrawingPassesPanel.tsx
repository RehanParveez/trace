import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, ErrorState, useToast } from "../../../../organizations/components/OrganizationUi";
import { takeoffErrorMessage } from "../../utils/errors";
import { useDrawingPasses, useTypeTankSize } from "../hooks/usePasses";
import { metres, pagesList, planText, REASON_TEXT, sizeValid, sourceTitle, TANK_TEXT } from "../utils/passes";
import type { DrawingPasses, ElectricalCoverage, TankKind, TankRecord, TankSource } from "../types/passes.types";
import { BasisChip } from "./BasisChip";

interface Props {
  drawingId: string;
  canEdit: boolean;
  version?: number;
}

const INPUT = "w-56 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-[12px]";
const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";

function SizeRow({ label, value, source }: { label: string; value: string; source: TankSource | undefined }) {
  return (
    <li className="flex flex-wrap items-center gap-2" data-testid={`tank-size-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <span className="w-28 text-[var(--color-text-secondary)]">{label}</span>
      <span className="font-semibold">{value}</span>
      <BasisChip route={source?.route} title={sourceTitle(source)} />
      {source?.page_no ? <span className={MUTED}>p.{source.page_no}</span> : null}
    </li>
  );
}

function TankCard({ tank, typed, canEdit, busy, onType }: { tank: TankRecord; typed: string | undefined; canEdit: boolean; busy: boolean; onType: (kind: TankKind, value: string | null) => void }) {
  const { t } = useTranslation();
  const [value, setValue] = useState(typed ?? "");
  const ok = sizeValid(value);
  return (
    <li className="space-y-2 rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`tank-record-${tank.kind}`} data-defaulted={tank.defaulted}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{t(`boq.takeoff.passes.tank.${tank.kind}`, TANK_TEXT[tank.kind])}</span>
        {tank.defaulted ? <Badge tone="gold">{t("boq.takeoff.passes.defaulted", "Plan assumed")}</Badge> : null}
        {typed ? <Badge tone="blue">{t("boq.takeoff.passes.typedBadge", "Size typed")}</Badge> : null}
        {tank.pages.length > 0 ? <span className={MUTED}>{t("boq.takeoff.passes.pages", "sheets {{pages}}", { pages: pagesList(tank.pages) })}</span> : null}
      </div>
      <ul className="space-y-1">
        <SizeRow label={t("boq.takeoff.passes.plan", "Plan, outside")} value={planText(tank)} source={tank.sources.plan} />
        <SizeRow label={t("boq.takeoff.passes.depth", "Depth")} value={metres(tank.depth_mm)} source={tank.sources.depth} />
        <SizeRow label={t("boq.takeoff.passes.wall", "Wall")} value={metres(tank.wall_mm)} source={tank.sources.wall} />
        <SizeRow label={t("boq.takeoff.passes.top", "Top slab")} value={metres(tank.top_mm)} source={tank.sources.top} />
        <SizeRow label={t("boq.takeoff.passes.base", "Base slab")} value={metres(tank.base_mm)} source={tank.sources.bottom} />
      </ul>
      {tank.defaulted ? <p className={MUTED}>{tank.sources.plan.text}</p> : null}
      {canEdit ? (
        <div className="flex flex-wrap items-center gap-2">
          <input className={INPUT} value={value} placeholder="2400 x 1700 or 2400 x 1700 x 2100 x 150" aria-label={t("boq.takeoff.passes.typeSize", "Type the size in mm")}
            onChange={(e) => setValue(e.target.value)} data-testid={`tank-size-input-${tank.kind}`} />
          <Button size="sm" disabled={busy || !ok} onClick={() => onType(tank.kind, value.trim())}>{t("boq.takeoff.passes.use", "Use this size")}</Button>
          {typed ? <Button size="sm" disabled={busy} onClick={() => { setValue(""); onType(tank.kind, null); }}>{t("boq.takeoff.passes.takeOff", "Take the typed size off")}</Button> : null}
          <span className={MUTED}>{t("boq.takeoff.passes.sizeHelp", "Length x width outside, in mm; or length x width x height x wall thickness.")}</span>
        </div>
      ) : null}
    </li>
  );
}

function TankRecords({ data, canEdit, busy, onType }: { data: DrawingPasses; canEdit: boolean; busy: boolean; onType: (kind: TankKind, value: string | null) => void }) {
  const { t } = useTranslation();
  if (data.tanks.length === 0) return null;
  const assumed = data.tanks.filter((x) => x.defaulted).length;
  return (
    <div className="space-y-2" data-testid="tank-records" data-assumed={assumed}>
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="font-semibold">{t("boq.takeoff.passes.tanksTitle", "Tanks")}</h4>
        {assumed > 0 ? <Badge tone="gold">{t("boq.takeoff.passes.tanksAssumed", "{{n}} with an assumed plan", { n: assumed })}</Badge> : <Badge tone="green">{t("boq.takeoff.passes.tanksPrinted", "All plans from the drawing")}</Badge>}
      </div>
      <ul className="space-y-2">
        {data.tanks.map((tank) => <TankCard key={`${tank.kind}-${data.typed[tank.kind] ?? ""}`} tank={tank} typed={data.typed[tank.kind]} canEdit={canEdit} busy={busy} onType={onType} />)}
      </ul>
    </div>
  );
}

function Coverage({ cov }: { cov: ElectricalCoverage }) {
  const { t } = useTranslation();
  const uncounted = cov.legend_symbols - cov.counted;
  return (
    <div className="space-y-2" data-testid="electrical-coverage" data-counted={cov.counted} data-rows={cov.legend_symbols}>
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="font-semibold">{t("boq.takeoff.passes.coverageTitle", "Electrical legend coverage")}</h4>
        <Badge tone={uncounted === 0 ? "green" : "gold"}>{t("boq.takeoff.passes.coverageCount", "{{n}} of {{m}} legend rows counted", { n: cov.counted, m: cov.legend_symbols })}</Badge>
        <span className={MUTED}>{t("boq.takeoff.passes.coveragePages", "plan pages {{pages}}", { pages: pagesList(cov.pages) })}</span>
      </div>
      <p className={MUTED}>{t("boq.takeoff.passes.coverageHelp", "Every legend row that found nothing on the plans says why. A row with no hit may be drawn differently on the plan, or not drawn at all.")}</p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[11.5px]">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-left">
              <th className="px-1 py-1">#</th>
              <th className="px-1 py-1">{t("boq.takeoff.passes.row", "Legend row")}</th>
              {cov.pages.map((p) => <th key={p} className="px-1 py-1 text-right">p.{p}</th>)}
              <th className="px-1 py-1 text-right">{t("boq.takeoff.passes.total", "Total")}</th>
              <th className="px-1 py-1">{t("boq.takeoff.passes.why", "Why none")}</th>
            </tr>
          </thead>
          <tbody>
            {cov.rows.map((r) => (
              <tr key={r.index} className="border-b border-[var(--color-border)] align-top" data-testid={`coverage-row-${r.index}`} data-total={r.total} data-reason={r.reason ?? ""}>
                <td className="px-1 py-1">{r.index}</td>
                <td className="px-1 py-1">{r.name}</td>
                {cov.pages.map((p) => <td key={p} className="px-1 py-1 text-right">{r.plan_counts[String(p)] ?? 0}</td>)}
                <td className="px-1 py-1 text-right font-semibold">{r.total}</td>
                <td className="px-1 py-1">{r.reason ? <span title={t(`boq.takeoff.passes.reason.${r.reason}`, REASON_TEXT[r.reason])}><Badge tone="slate">{r.reason}</Badge></span> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function DrawingPassesPanel({ drawingId, canEdit, version }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const q = useDrawingPasses(drawingId, version);
  const type = useTypeTankSize(drawingId);
  if (q.isError && !q.data) return <ErrorState title={t("boq.takeoff.passes.error", "Couldn't load the tank records and the electrical coverage")} onRetry={() => void q.refetch()} />;
  const data = q.data;
  if (!data || !data.ran || (data.tanks.length === 0 && !data.electrical)) return null;
  const onType = (kind: TankKind, value: string | null) => type.mutate({ kind, value }, {
    onSuccess: () => showToast({ tone: "success", title: value ? t("boq.takeoff.passes.typed", "Size saved; the tank was worked out again") : t("boq.takeoff.passes.takenOff", "Typed size taken off") }),
    onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.passes.failed", "Could not save the size"), description: takeoffErrorMessage(e) }),
  });
  return (
    <section className="space-y-3 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="drawing-passes">
      <TankRecords data={data} canEdit={canEdit} busy={type.isPending} onType={onType} />
      {data.electrical ? <Coverage cov={data.electrical} /> : null}
    </section>
  );
}
