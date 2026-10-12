import { useTranslation } from "react-i18next";
import type { SnapKind } from "../types/takeoff.types";
import type { Tool } from "../store/takeoffView.store";

interface Props {
  tool: Tool;
  onTool: (tool: Tool) => void;
  canDraw: boolean;
  reason: string | null;
  canPick: boolean;
  snapOn: boolean;
  snapAvailable: boolean;
  snapKinds: SnapKind[];
  onToggleSnap: () => void;
  onToggleKind: (kind: SnapKind) => void;
  ortho: boolean;
  onOrtho: () => void;
  showMeasurements: boolean;
  onToggleMeasurements: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
}

const TOOLS: Array<{ tool: Tool; key: string; label: string; draws: boolean; picks?: boolean }> = [
  { tool: "select", key: "V", label: "Select", draws: false },
  { tool: "pan", key: "H", label: "Pan", draws: false },
  { tool: "ruler", key: "R", label: "Ruler", draws: false },
  { tool: "length", key: "L", label: "Length", draws: true },
  { tool: "area", key: "A", label: "Area", draws: true },
  { tool: "count", key: "C", label: "Count", draws: true },
  { tool: "wall", key: "W", label: "Wall", draws: true, picks: true },
  { tool: "room", key: "P", label: "Room", draws: true, picks: true },
];

const KIND_LABEL: Record<SnapKind, string> = { ENDPOINT: "End", INTERSECTION: "Cross", MIDPOINT: "Mid", EDGE: "Edge" };

function Chip({ active, disabled, title, onClick, children, testId }: { active?: boolean; disabled?: boolean; title?: string; onClick: () => void; children: React.ReactNode; testId?: string }) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      aria-pressed={active}
      data-testid={testId}
      onClick={onClick}
      className={`min-h-8 rounded-[7px] border px-2.5 text-[12.5px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        active ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-text-primary)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]"
      }`}
    >
      {children}
    </button>
  );
}

export function Toolbar(p: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2" role="toolbar" aria-label="Takeoff tools" data-testid="toolbar">
      {TOOLS.map((x) => {
        const off = x.draws && (!p.canDraw || (x.picks && !p.canPick));
        const title = off ? (p.reason ?? (x.picks ? t("boq.takeoff.tool.needsVector", "Needs a vector sheet") : "")) : `${x.label} (${x.key})`;
        return (
          <Chip key={x.tool} active={p.tool === x.tool} disabled={off} title={title} onClick={() => p.onTool(x.tool)} testId={`tool-${x.tool}`}>
            {t(`boq.takeoff.tool.${x.tool}`, x.label)} <span className="ml-1 font-mono text-[10.5px] opacity-60">{x.key}</span>
          </Chip>
        );
      })}
      <span className="mx-1 h-5 w-px bg-[var(--color-border)]" />
      <Chip active={p.snapOn && p.snapAvailable} disabled={!p.snapAvailable} title={p.snapAvailable ? t("boq.takeoff.snap.title", "Snap to the drawing's lines (S)") : t("boq.takeoff.snap.none", "No lines to snap to on this sheet")} onClick={p.onToggleSnap} testId="snap-toggle">
        {t("boq.takeoff.snap.label", "Snap")}
      </Chip>
      {p.snapOn && p.snapAvailable
        ? (Object.keys(KIND_LABEL) as SnapKind[]).map((k) => (
            <Chip key={k} active={p.snapKinds.includes(k)} onClick={() => p.onToggleKind(k)} title={k.toLowerCase()}>
              {KIND_LABEL[k]}
            </Chip>
          ))
        : null}
      <Chip active={p.ortho} onClick={p.onOrtho} title={t("boq.takeoff.ortho.title", "Keep lines horizontal or vertical (O, or hold Shift)")} testId="ortho-toggle">
        {t("boq.takeoff.ortho.label", "Ortho")}
      </Chip>
      <span className="mx-1 h-5 w-px bg-[var(--color-border)]" />
      <Chip active={p.showMeasurements} onClick={p.onToggleMeasurements} title={t("boq.takeoff.showMeasurements", "Show or hide measurements")}>
        {t("boq.takeoff.marks", "Marks")}
      </Chip>
      <Chip onClick={p.onZoomOut} title="Zoom out (-)">−</Chip>
      <Chip onClick={p.onFit} title="Fit sheet (F)" testId="fit">{t("boq.takeoff.fit", "Fit")}</Chip>
      <Chip onClick={p.onZoomIn} title="Zoom in (+)">+</Chip>
    </div>
  );
}
