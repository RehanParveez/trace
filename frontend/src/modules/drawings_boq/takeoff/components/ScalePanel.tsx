import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Field, inputClass, Toggle } from "../../../organizations/components/OrganizationUi";
import type { LengthUnit, Pt, SheetAnalysis, TakeoffCalibration, TakeoffSheet } from "../types/takeoff.types";
import { dist } from "../utils/geometry";
import { fmtPlain, fmtRatio } from "../utils/format";
import { AGREEMENT, checkBand, needsAcknowledgement, noteInfo } from "../utils/scaleText";

export interface CaptureState { target: "ref" | "check" | null; ref: Pt[]; check: Pt[] }

interface Props {
  sheet: TakeoffSheet;
  calibrations: TakeoffCalibration[];
  analysis: SheetAnalysis | undefined;
  analysisLoading: boolean;
  canEdit: boolean;
  busy: boolean;
  capture: CaptureState;
  onCapture: (target: "ref" | "check" | null) => void;
  onClearCapture: () => void;
  onAuto: (use: "RECOMMENDED" | "DECLARED" | "DIMENSIONS" | "ROOMS", includeRegions: boolean) => void;
  onManual: (body: { method: "TWO_POINT" | "SCALE_RATIO"; scale_text?: string; ref?: { p1: Pt; p2: Pt; value: string; unit: LengthUnit }; check?: { p1: Pt; p2: Pt; value: string; unit: LengthUnit } }) => void;
  onMakeDefault: (id: string) => void;
  onDelete: (id: string) => void;
  showDims: boolean;
  onToggleDims: () => void;
  alignmentNote: string | null;
}

const UNITS: LengthUnit[] = ["mm", "cm", "m", "ft", "in"];

function CalRow({ c, canEdit, onMakeDefault, onDelete }: { c: TakeoffCalibration; canEdit: boolean; onMakeDefault: () => void; onDelete: () => void }) {
  const { t } = useTranslation();
  const band = checkBand(c.check_error_pct);
  return (
    <li className={`rounded-[8px] border p-2.5 text-[12.5px] ${c.is_default ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`} data-testid="calibration-row">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-[var(--color-text-primary)]">{c.label ?? (c.ratio ? fmtRatio(c.ratio) : c.method)}</span>
        {c.is_default ? <Badge tone="gold">{t("boq.takeoff.scale.default", "In use")}</Badge> : null}
        {!c.usable ? <Badge tone="red">{t("boq.takeoff.scale.notUsable", "Not usable")}</Badge> : null}
        <Badge tone={band.tone}>{`${t("boq.takeoff.scale.factor", "factor")} ${fmtPlain(c.quality_factor, 2)}`}</Badge>
      </div>
      <div className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">
        {c.usable ? band.text : c.reason}
        {c.mm_per_pt ? <span className="ml-2 font-mono">{fmtPlain(c.mm_per_pt, 4)} mm/pt</span> : null}
      </div>
      {canEdit ? (
        <div className="mt-1.5 flex gap-2">
          {!c.is_default && c.usable ? <button type="button" className="text-[12px] font-semibold text-[var(--color-info)]" onClick={onMakeDefault}>{t("boq.takeoff.scale.makeDefault", "Use this one")}</button> : null}
          <button type="button" className="text-[12px] font-semibold text-[var(--color-danger)]" onClick={onDelete}>{t("boq.takeoff.scale.remove", "Remove")}</button>
        </div>
      ) : null}
    </li>
  );
}

export function ScalePanel(p: Props) {
  const { t } = useTranslation();
  const scale = p.analysis?.detected_scale;
  const rec = scale?.recommended ?? null;
  const agreement = scale?.agreement ? AGREEMENT[scale.agreement] : undefined;
  const ack = needsAcknowledgement(scale);
  const [acknowledged, setAcknowledged] = useState(false);
  const [refValue, setRefValue] = useState("");
  const [refUnit, setRefUnit] = useState<LengthUnit>("mm");
  const [chkValue, setChkValue] = useState("");
  const [chkUnit, setChkUnit] = useState<LengthUnit>("mm");
  const [scaleText, setScaleText] = useState("");
  const [mode, setMode] = useState<"TWO_POINT" | "SCALE_RATIO">("TWO_POINT");
  const rooms = (scale?.witnesses ?? []).find((w) => w.source === "ROOM_LABELS" && w.ratio) ?? null;
  const pairs = scale?.measured?.pairs ?? [];
  const regions = (scale?.measured?.clusters ?? []).length > 1 && scale?.agreement === "MULTI_SCALE";
  const diag = Math.hypot(Number(p.sheet.width_pt), Number(p.sheet.height_pt));
  const refLen = p.capture.ref.length === 2 ? dist(p.capture.ref[0], p.capture.ref[1]) : 0;
  const short = refLen > 0 && refLen < diag * 0.05;
  const hasDefault = p.calibrations.some((c) => c.is_default && c.usable);
  const raster = p.sheet.content_kind === "RASTER";

  const canCreateTwoPoint = p.capture.ref.length === 2 && Number(refValue) > 0 && (p.capture.check.length === 0 || (p.capture.check.length === 2 && Number(chkValue) > 0));
  const canCreateRatio = scaleText.trim().length > 0 && (p.capture.check.length === 0 || (p.capture.check.length === 2 && Number(chkValue) > 0));

  return (
    <div className="space-y-4 p-4" data-testid="scale-panel">
      {p.alignmentNote ? <div className="rounded-[8px] bg-[var(--color-danger-bg)] p-2.5 text-[12.5px] text-[var(--color-danger)]" data-testid="alignment-note">{p.alignmentNote}</div> : null}

      <section>
        <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.scale.calibrations", "Calibration of this sheet")}</h3>
        {!hasDefault ? (
          <div className="mb-2 rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px] text-[var(--color-text-primary)]" data-testid="uncalibrated">
            {t("boq.takeoff.scale.needed", "No scale yet. Measuring is locked until this sheet is calibrated.")}
          </div>
        ) : null}
        {p.calibrations.length === 0 ? null : (
          <ul className="space-y-2">
            {p.calibrations.map((c) => (
              <CalRow key={c.id} c={c} canEdit={p.canEdit && !p.busy} onMakeDefault={() => p.onMakeDefault(c.id)} onDelete={() => p.onDelete(c.id)} />
            ))}
          </ul>
        )}
      </section>

      {p.sheet.prep_status === "READY" ? (
        <section className="rounded-[10px] border border-[var(--color-border)] p-3" data-testid="scale-finder">
          <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.scale.finder", "Scale finder")}</h3>
          {p.analysisLoading ? <div className="text-[12.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.loading", "Loading…")}</div> : null}
          {agreement ? (
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge tone={agreement.tone}>{scale?.agreement?.replace(/_/g, " ").toLowerCase()}</Badge>
              <span className="text-[12.5px] text-[var(--color-text-secondary)]">{agreement.text}</span>
            </div>
          ) : null}
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[12.5px]">
            <dt className="text-[var(--color-text-muted)]">{t("boq.takeoff.scale.printed", "Printed scale")}</dt>
            <dd className="font-mono">{scale?.declared?.primary ? fmtRatio(scale.declared.primary.ratio) : "—"}</dd>
            <dt className="text-[var(--color-text-muted)]">{t("boq.takeoff.scale.measured", "From dimensions")}</dt>
            <dd className="font-mono">{scale?.measured?.clusters?.[0] ? `${fmtRatio(scale.measured.clusters[0].ratio)} (${scale.measured.clusters[0].support} dims)` : "—"}</dd>
            <dt className="text-[var(--color-text-muted)]">{t("boq.takeoff.scale.fromRooms", "From room sizes")}</dt>
            <dd className="font-mono" data-testid="scale-from-rooms">{rooms ? `${fmtRatio(rooms.ratio as number)} (${rooms.support} rooms${rooms.strong ? "" : ", not firm"})` : "—"}</dd>
            <dt className="text-[var(--color-text-muted)]">{t("boq.takeoff.scale.paper", "Paper")}</dt>
            <dd className="font-mono">{scale?.paper?.name ?? "—"}</dd>
          </dl>
          {(scale?.notes ?? []).length > 0 ? (
            <ul className="mt-2 space-y-1">
              {scale!.notes!.map((n, i) => {
                const info = noteInfo(n);
                return (
                  <li key={`${n.code}-${i}`} className={`rounded-[6px] px-2 py-1 text-[12px] ${info.tone === "red" ? "bg-[var(--color-danger-bg)] text-[var(--color-danger)]" : info.tone === "gold" ? "bg-[var(--color-warning-bg)] text-[var(--color-text-primary)]" : "bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]"}`}>
                    <span className="font-mono text-[10.5px] font-semibold">{n.code}</span> {info.text}
                  </li>
                );
              })}
            </ul>
          ) : null}
          {rec ? (
            <div className="mt-3 rounded-[8px] bg-[var(--color-surface-muted)] p-2.5">
              <div className="text-[12.5px]">
                {t("boq.takeoff.scale.recommended", "Recommended")}: <span className="font-mono font-semibold" data-testid="recommended-ratio">{fmtRatio(rec.ratio)}</span>
                <span className="ml-2 text-[11.5px] text-[var(--color-text-muted)]">{rec.basis.replace(/_/g, " ").toLowerCase()} · trust {Math.round(rec.trust * 100)}%</span>
              </div>
              {ack ? (
                <label className="mt-2 flex items-start gap-2 text-[12px] text-[var(--color-danger)]">
                  <input type="checkbox" className="mt-0.5" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} data-testid="ack" />
                  {t("boq.takeoff.scale.ack", "I understand the printed scale and the dimensions disagree, and I choose this scale on purpose.")}
                </label>
              ) : null}
              {p.canEdit ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button size="sm" variant="primary" disabled={p.busy || (ack && !acknowledged)} onClick={() => p.onAuto("RECOMMENDED", false)} data-testid="use-recommended">
                    {t("boq.takeoff.scale.useRecommended", "Use recommended")}
                  </Button>
                  {scale?.declared?.primary ? (
                    <Button size="sm" disabled={p.busy || (ack && !acknowledged)} onClick={() => p.onAuto("DECLARED", false)}>{t("boq.takeoff.scale.usePrinted", "Use printed scale")}</Button>
                  ) : null}
                  {(scale?.measured?.clusters?.[0]?.support ?? 0) >= 2 ? (
                    <Button size="sm" disabled={p.busy || (ack && !acknowledged)} onClick={() => p.onAuto("DIMENSIONS", false)}>{t("boq.takeoff.scale.useMeasured", "Use measured scale")}</Button>
                  ) : null}
                  {rooms?.strong ? (
                    <Button size="sm" disabled={p.busy || (ack && !acknowledged)} onClick={() => p.onAuto("ROOMS", false)} data-testid="use-rooms">{t("boq.takeoff.scale.useRooms", "Use room-size scale")}</Button>
                  ) : null}
                  {regions ? (
                    <Button size="sm" disabled={p.busy} onClick={() => p.onAuto("RECOMMENDED", true)}>{t("boq.takeoff.scale.regions", "One calibration per scale region")}</Button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-2 text-[12.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.scale.noRecommendation", "No automatic recommendation. Calibrate by hand below.")}</div>
          )}
          {pairs.length > 0 ? (
            <div className="mt-3 flex items-center justify-between">
              <span className="text-[12.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.scale.audit", "Show printed dimensions on the sheet")} ({pairs.length})</span>
              <Toggle checked={p.showDims} onChange={p.onToggleDims} label="Show printed dimensions" />
            </div>
          ) : null}
        </section>
      ) : null}

      {p.canEdit ? (
        <section className="rounded-[10px] border border-[var(--color-border)] p-3" data-testid="manual-calibration">
          <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.scale.manual", "Calibrate by hand")}</h3>
          {raster ? <div className="mb-2 rounded-[6px] bg-[var(--color-warning-bg)] px-2 py-1 text-[12px]">{t("boq.takeoff.scale.rasterNote", "Scanned sheet: pick two points on a long printed dimension and add a check dimension.")}</div> : null}
          <div className="mb-2 flex gap-2">
            <button type="button" className={`rounded-[7px] border px-2.5 py-1 text-[12px] font-semibold ${mode === "TWO_POINT" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`} onClick={() => setMode("TWO_POINT")}>{t("boq.takeoff.scale.twoPoint", "Two points")}</button>
            <button type="button" className={`rounded-[7px] border px-2.5 py-1 text-[12px] font-semibold ${mode === "SCALE_RATIO" ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]" : "border-[var(--color-border)]"}`} onClick={() => setMode("SCALE_RATIO")}>{t("boq.takeoff.scale.typed", "Type the scale")}</button>
          </div>

          {mode === "TWO_POINT" ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Button size="sm" variant={p.capture.target === "ref" ? "primary" : "secondary"} onClick={() => p.onCapture("ref")} data-testid="pick-ref">
                  {p.capture.ref.length === 2 ? t("boq.takeoff.scale.repick", "Pick again") : t("boq.takeoff.scale.pickTwo", "Pick the two points")}
                </Button>
                <span className="text-[12px] text-[var(--color-text-muted)]">{p.capture.ref.length}/2 · {refLen ? `${refLen.toFixed(1)} pt` : ""}</span>
              </div>
              <div className="grid grid-cols-[1fr_84px] gap-2">
                <Field label={t("boq.takeoff.scale.knownDistance", "Real distance between them")}>
                  <input className={inputClass} value={refValue} inputMode="decimal" onChange={(e) => setRefValue(e.target.value)} data-testid="ref-value" />
                </Field>
                <Field label={t("boq.takeoff.scale.unit", "Unit")}>
                  <select className={inputClass} value={refUnit} onChange={(e) => setRefUnit(e.target.value as LengthUnit)}>{UNITS.map((u) => (<option key={u}>{u}</option>))}</select>
                </Field>
              </div>
              {short ? <div className="rounded-[6px] bg-[var(--color-warning-bg)] px-2 py-1 text-[12px]">{t("boq.takeoff.scale.short", "These points are close together, which magnifies picking error across the sheet. Use the longest known dimension you can.")}</div> : null}
            </div>
          ) : (
            <Field label={t("boq.takeoff.scale.scaleText", "Scale as printed")} hint={t("boq.takeoff.scale.scaleHint", "1:100  or  1/8\" = 1'-0\"")}>
              <input className={inputClass} value={scaleText} onChange={(e) => setScaleText(e.target.value)} data-testid="scale-text" />
            </Field>
          )}

          <div className="mt-3 space-y-2 border-t border-[var(--color-border)] pt-3">
            <div className="text-[12px] font-semibold text-[var(--color-text-secondary)]">{t("boq.takeoff.scale.check", "Check dimension (strongly recommended)")}</div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant={p.capture.target === "check" ? "primary" : "secondary"} onClick={() => p.onCapture("check")} data-testid="pick-check">
                {p.capture.check.length === 2 ? t("boq.takeoff.scale.repick", "Pick again") : t("boq.takeoff.scale.pickCheck", "Pick a second known length")}
              </Button>
              <span className="text-[12px] text-[var(--color-text-muted)]">{p.capture.check.length}/2</span>
            </div>
            {p.capture.check.length === 2 ? (
              <div className="grid grid-cols-[1fr_84px] gap-2">
                <input className={inputClass} placeholder="real distance" value={chkValue} inputMode="decimal" onChange={(e) => setChkValue(e.target.value)} data-testid="check-value" />
                <select className={inputClass} value={chkUnit} onChange={(e) => setChkUnit(e.target.value as LengthUnit)}>{UNITS.map((u) => (<option key={u}>{u}</option>))}</select>
              </div>
            ) : null}
          </div>

          <div className="mt-3 flex gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={p.busy || (mode === "TWO_POINT" ? !canCreateTwoPoint : !canCreateRatio)}
              data-testid="create-calibration"
              onClick={() => {
                const check = p.capture.check.length === 2 ? { p1: p.capture.check[0], p2: p.capture.check[1], value: chkValue, unit: chkUnit } : undefined;
                if (mode === "TWO_POINT") p.onManual({ method: "TWO_POINT", ref: { p1: p.capture.ref[0], p2: p.capture.ref[1], value: refValue, unit: refUnit }, check });
                else p.onManual({ method: "SCALE_RATIO", scale_text: scaleText.trim(), check });
              }}
            >
              {t("boq.takeoff.scale.create", "Create calibration")}
            </Button>
            <Button size="sm" variant="ghost" onClick={p.onClearCapture}>{t("boq.takeoff.scale.clear", "Clear points")}</Button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
