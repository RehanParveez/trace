import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState } from "../../../organizations/components/OrganizationUi";
import type { Frame, FrameView } from "../types/takeoff.types";
import { addNudge, fitTo, frameBounds, memberBox, methodLabel, openCount, shiftToSave, toScreen, viewColor, viewState } from "../utils/frame";

interface Props {
  frame: Frame | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  canEdit: boolean;
  busy: boolean;
  onPlace: (body: { view: string; action: "CONFIRM" | "SET" | "CLEAR"; dx_mm?: number; dy_mm?: number }) => void;
  onReference: (view: string) => void;
}

const W = 376, H = 280;
const STEPS = [10, 100, 1000];

export function FramePanel(p: Props) {
  const { t } = useTranslation();
  const [nudges, setNudges] = useState<Record<string, [number, number]>>({});
  const [step, setStep] = useState(100);
  const [pickedKey, setPickedKey] = useState<string | null>(null);
  const frame = p.frame;
  const bounds = useMemo(() => (frame ? frameBounds(frame, nudges) : null), [frame, nudges]);
  if (p.loading) return <LoadingState label={t("boq.takeoff.loading", "Loading…")} />;
  if (p.error) return <ErrorState title={t("boq.takeoff.frame.error", "Couldn't load the building frame")} onRetry={p.onRetry} />;
  if (!frame || frame.views.length === 0) {
    return (
      <div className="p-4" data-testid="frame-empty">
        <EmptyState icon="info" title={t("boq.takeoff.frame.none", "No placed members yet")} description={t("boq.takeoff.frame.noneDesc", "Confirm counted columns, footings or slabs measured on a scaled sheet. Their views then appear here to be placed on the building.")} />
      </div>
    );
  }
  const fit = bounds ? fitTo(bounds, W, H) : null;
  const picked = frame.views.find((v) => v.key === pickedKey) ?? frame.views[0];
  const open = openCount(frame);

  const nudge = (v: FrameView, dx: number, dy: number) => setNudges((n) => ({ ...n, [v.key]: addNudge(n[v.key], dx, dy) }));
  const reset = (key: string) => setNudges((n) => { const { [key]: _gone, ...rest } = n; return rest; });
  const save = (v: FrameView) => {
    const [dx, dy] = shiftToSave(v, nudges[v.key]);
    p.onPlace({ view: v.key, action: "SET", dx_mm: dx, dy_mm: dy });
    reset(v.key);
  };

  return (
    <div className="space-y-3 p-4" data-testid="frame-panel" data-status={frame.status}>
      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        <Badge tone={frame.status === "CONFIRMED" ? "green" : "gold"}>{frame.status === "CONFIRMED" ? t("boq.takeoff.frame.confirmed", "Placement confirmed") : t("boq.takeoff.frame.assumed", "Placement assumed")}</Badge>
        {open > 0 ? <span className="text-[var(--color-text-secondary)]" data-testid="frame-open">{t("boq.takeoff.frame.open", "{{n}} view(s) still need you", { n: open })}</span> : null}
      </div>
      <p className="text-[12px] text-[var(--color-text-secondary)]">
        {t("boq.takeoff.frame.help", "Every view is placed on one building frame so a column can be matched to the slab it carries. Until you confirm a view, its placement is an assumption and anything taken off because of it is marked uncertain.")}
      </p>

      {fit ? (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)]" role="img" aria-label={t("boq.takeoff.frame.overlay", "Views on the building frame")} data-testid="frame-overlay">
          {frame.views.map((v, vi) => {
            const [nx, ny] = nudges[v.key] ?? [0, 0];
            const faded = v.key !== picked.key;
            return (
              <g key={v.key} data-testid={`frame-view-${vi}`} opacity={faded ? 0.45 : 1}>
                {v.members.map((m, i) => {
                  const b = memberBox(m, nx, ny);
                  if (!b) return null;
                  const s = toScreen(fit, b);
                  return <rect key={`${m.measurement_id}-${m.instance}-${i}`} x={s.x} y={s.y} width={Math.max(s.w, 2)} height={Math.max(s.h, 2)} fill={viewColor(vi)} fillOpacity={m.category === "SLAB" ? 0.12 : 0.55} stroke={viewColor(vi)} strokeWidth={1} strokeDasharray={v.grade === "CONFIRMED" ? undefined : "3 2"} />;
                })}
              </g>
            );
          })}
        </svg>
      ) : (
        <div className="rounded-[8px] border border-dashed border-[var(--color-border)] p-3 text-[12px] text-[var(--color-text-muted)]" data-testid="frame-unplaced-all">
          {t("boq.takeoff.frame.nothingPlaced", "No view could be placed yet. Place one by hand below.")}
        </div>
      )}

      <ul className="space-y-2" data-testid="frame-views">
        {frame.views.map((v, vi) => {
          const state = viewState(v);
          const [nx, ny] = nudges[v.key] ?? [0, 0];
          const moved = nx !== 0 || ny !== 0;
          const isPicked = v.key === picked.key;
          return (
            <li key={v.key} className={`rounded-[8px] border p-2 text-[12px] ${isPicked ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"}`} data-testid={`frame-row-${vi}`} data-state={state}>
              <button type="button" className="flex w-full items-center gap-2 text-left" onClick={() => setPickedKey(v.key)} aria-pressed={isPicked}>
                <span className="inline-block h-3 w-3 shrink-0 rounded-sm" style={{ background: viewColor(vi) }} />
                <span className="min-w-0 flex-1 truncate font-semibold" title={v.key}>{v.key}</span>
                {v.reference ? <Badge tone="blue">{t("boq.takeoff.frame.reference", "reference")}</Badge> : null}
                {state === "DONE" ? <Badge tone="green">{t("boq.takeoff.frame.done", "confirmed")}</Badge> : state === "GUESS" ? <Badge tone="gold">{t("boq.takeoff.frame.guess", "assumed")}</Badge> : <Badge tone="red">{t("boq.takeoff.frame.unplaced", "not placed")}</Badge>}
              </button>
              <div className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">
                {methodLabel(v)} · {v.members.length} {t("boq.takeoff.frame.marks", "marks")}
                {v.method === "ENVELOPE" ? ` · ${t("boq.takeoff.frame.lowConfidence", "low confidence, check it")}` : null}
                {v.method === "COLUMN_MATCH" ? ` · ${t("boq.takeoff.frame.residual", "worst gap {{mm}} mm", { mm: v.residual_mm })}` : null}
              </div>
              {isPicked && p.canEdit ? (
                <div className="mt-2 space-y-2" data-testid="frame-controls">
                  <div className="flex flex-wrap items-center gap-1 text-[11.5px]">
                    <span>{t("boq.takeoff.frame.step", "Step")}</span>
                    {STEPS.map((s) => (
                      <button key={s} type="button" className={`rounded px-2 py-0.5 ${step === s ? "bg-[var(--color-trace-gold)] text-black" : "bg-[var(--color-surface-muted)]"}`} onClick={() => setStep(s)} data-testid={`frame-step-${s}`}>{s} mm</button>
                    ))}
                    <span className="ml-2 font-mono" data-testid="frame-shift">dx {shiftToSave(v, nudges[v.key])[0]} · dy {shiftToSave(v, nudges[v.key])[1]}</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {!v.reference ? (
                      <>
                        <Button size="sm" variant="secondary" onClick={() => nudge(v, -step, 0)} aria-label="left" data-testid="frame-left">←</Button>
                        <Button size="sm" variant="secondary" onClick={() => nudge(v, step, 0)} aria-label="right" data-testid="frame-right">→</Button>
                        <Button size="sm" variant="secondary" onClick={() => nudge(v, 0, step)} aria-label="up" data-testid="frame-up">↑</Button>
                        <Button size="sm" variant="secondary" onClick={() => nudge(v, 0, -step)} aria-label="down" data-testid="frame-down">↓</Button>
                      </>
                    ) : null}
                    {moved ? <Button size="sm" variant="primary" disabled={p.busy} onClick={() => save(v)} data-testid="frame-save">{t("boq.takeoff.frame.save", "Save placement")}</Button> : null}
                    {moved ? <Button size="sm" variant="ghost" onClick={() => reset(v.key)}>{t("boq.takeoff.frame.undo", "Undo")}</Button> : null}
                    {!moved && state !== "DONE" && v.method !== "UNALIGNED" ? <Button size="sm" variant="primary" disabled={p.busy} onClick={() => p.onPlace({ view: v.key, action: "CONFIRM" })} data-testid="frame-confirm">{t("boq.takeoff.frame.confirm", "This is right")}</Button> : null}
                    {!moved && v.decided && !v.reference ? <Button size="sm" variant="ghost" disabled={p.busy} onClick={() => p.onPlace({ view: v.key, action: "CLEAR" })} data-testid="frame-clear">{t("boq.takeoff.frame.clear", "Let the engine place it")}</Button> : null}
                    {!v.reference ? <Button size="sm" variant="ghost" disabled={p.busy} onClick={() => p.onReference(v.key)} data-testid="frame-make-reference">{t("boq.takeoff.frame.makeReference", "Make this the reference")}</Button> : null}
                  </div>
                  {!v.reference ? <p className="text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.frame.referenceWarn", "Changing the reference clears the placements you saved, because they are measured against it.")}</p> : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
      {frame.cleared_placements > 0 ? <p className="text-[11.5px] text-[var(--color-warning)]" data-testid="frame-cleared">{t("boq.takeoff.frame.cleared", "{{n}} earlier placement(s) were cleared.", { n: frame.cleared_placements })}</p> : null}
      <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.frame.runAgain", "Run the calculation again after changing a placement.")}</p>
    </div>
  );
}
