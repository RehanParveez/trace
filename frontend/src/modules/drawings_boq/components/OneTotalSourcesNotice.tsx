import { useTranslation } from "react-i18next";
import { useOneTotalSources } from "../hooks/useOneTotal";
import { useSaveMeasurementParameters } from "../hooks/useMeasurementParams";
import { sourcesNotice } from "../utils/oneTotalRules";

const BTN = "rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1 text-[11px] font-semibold text-[var(--color-text-primary)] hover:bg-[var(--color-surface-muted)] disabled:opacity-50";

export function OneTotalSourcesNotice({ projectId }: { projectId: string }) {
  const { t } = useTranslation();
  const sources = useOneTotalSources(projectId);
  const save = useSaveMeasurementParameters(projectId);
  const notice = sourcesNotice(sources.data);
  if (notice.tone === "none") return null;
  const change = (value: number | null) => save.mutate({ one_total: value }, { onSuccess: () => void sources.refetch() });
  return (
    <div
      data-testid="one-total-sources"
      data-tone={notice.tone}
      className={`space-y-2 rounded-[8px] border px-3 py-2 text-[12px] ${notice.tone === "warn" ? "border-[var(--color-warning)]/40 bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]"}`}
    >
      <p>{t(`boq.oneTotal.sources.${notice.tone}.${sources.data?.one_total.source ?? "detected"}`, notice.text)}</p>
      <div className="flex flex-wrap gap-2">
        {notice.canSwitchOn ? <button type="button" className={BTN} disabled={save.isPending} onClick={() => change(1)}>{t("boq.oneTotal.sources.switchOn", "Switch one total on")}</button> : null}
        {notice.canSwitchOff ? <button type="button" className={BTN} disabled={save.isPending} onClick={() => change(0)}>{t("boq.oneTotal.sources.switchOff", "Switch it off")}</button> : null}
        {notice.canGoAutomatic ? <button type="button" className={BTN} disabled={save.isPending} onClick={() => change(null)}>{t("boq.oneTotal.sources.automatic", "Decide it from the project again")}</button> : null}
      </div>
      {save.isError ? <p className="text-[var(--color-danger)]">{t("boq.oneTotal.sources.failed", "Could not save that. Try again.")}</p> : null}
    </div>
  );
}
