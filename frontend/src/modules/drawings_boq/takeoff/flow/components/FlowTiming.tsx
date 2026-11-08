import { useTranslation } from "react-i18next";
import { TableShell } from "../../../../organizations/components/OrganizationUi";
import type { Sitting } from "../types/flow.types";
import { SEGMENT_TEXT, secondsText } from "../utils/flow";

export function FlowTiming({ sitting }: { sitting: Sitting }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3" data-testid="flow-timing">
      <div className="text-[13px]">
        <span className="font-semibold">{t("boq.flow.sittingTime", "Time of the sitting")}: </span>
        <span className="font-mono" data-testid="flow-sitting-seconds">{secondsText(sitting.sitting_seconds)}</span>
        {sitting.complete ? null : <span className="text-[var(--color-text-muted)]"> {t("boq.flow.sittingOpen", "(complete after the first export)")}</span>}
      </div>
      <TableShell>
        <table className="w-full text-left text-[12.5px]">
          <tbody>
            {sitting.segments.map((s) => (
              <tr key={s.name} className="border-t border-[var(--color-border)] first:border-t-0">
                <td className="px-3 py-1.5">{SEGMENT_TEXT[s.name] ?? s.name}</td>
                <td className="px-3 py-1.5 text-right font-mono">{secondsText(s.seconds)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableShell>
      {sitting.stages.length > 0 ? (
        <TableShell>
          <table className="w-full text-left text-[12.5px]" data-testid="flow-stage-seconds">
            <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase text-[var(--color-text-muted)]">
              <tr><th className="px-3 py-1.5">{t("boq.flow.stage", "Reader stage")}</th><th className="px-3 py-1.5 text-right">{t("boq.flow.stageSeconds", "Seconds")}</th></tr>
            </thead>
            <tbody>
              {sitting.stages.map((s) => (
                <tr key={s.name} className="border-t border-[var(--color-border)]">
                  <td className="px-3 py-1.5">{s.name}{s.status === "DONE" ? "" : ` (${s.status})`}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{s.seconds.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      ) : null}
    </div>
  );
}
