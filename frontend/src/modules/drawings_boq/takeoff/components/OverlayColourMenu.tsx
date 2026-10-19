import { useTranslation } from "react-i18next";
import { CHECK_COLOUR, CHECK_TEXT, GRADE_COLOUR, GRADE_TEXT, MODE_TEXT, OVERLAY_MODES } from "../utils/overlayColour";
import type { OverlayMode } from "../utils/overlayColour";

interface Props {
  mode: OverlayMode;
  onMode: (mode: OverlayMode) => void;
}

function Swatch({ colour, text }: { colour: string; text: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colour }} />
      {text}
    </span>
  );
}

export function OverlayColourMenu({ mode, onMode }: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] px-4 py-1 text-[11.5px] text-[var(--color-text-secondary)]" data-testid="overlay-colour" data-mode={mode}>
      <label className="flex items-center gap-1.5">
        <span className="font-semibold">{t("boq.takeoff.overlay.title", "Colour marks")}</span>
        <select
          className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5"
          value={mode}
          onChange={(e) => onMode(e.target.value as OverlayMode)}
          aria-label={t("boq.takeoff.overlay.title", "Colour marks")}
          data-testid="overlay-colour-select"
        >
          {OVERLAY_MODES.map((m) => (
            <option key={m} value={m}>{t(`boq.takeoff.overlay.mode.${m}`, MODE_TEXT[m])}</option>
          ))}
        </select>
      </label>
      {mode === "CHECK" ? (
        <span className="flex flex-wrap items-center gap-3" data-testid="overlay-legend-check">
          {(Object.keys(CHECK_COLOUR) as Array<keyof typeof CHECK_COLOUR>).map((k) => <Swatch key={k} colour={CHECK_COLOUR[k]} text={t(`boq.takeoff.overlay.check.${k}`, CHECK_TEXT[k])} />)}
        </span>
      ) : null}
      {mode === "GRADE" ? (
        <span className="flex flex-wrap items-center gap-3" data-testid="overlay-legend-grade">
          {(Object.keys(GRADE_COLOUR) as Array<keyof typeof GRADE_COLOUR>).map((k) => <Swatch key={k} colour={GRADE_COLOUR[k]} text={t(`boq.takeoff.overlay.grade.${k}`, GRADE_TEXT[k])} />)}
        </span>
      ) : null}
    </div>
  );
}
