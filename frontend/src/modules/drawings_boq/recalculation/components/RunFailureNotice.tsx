import { Button } from "../../../organizations/components/OrganizationUi";
import { runFailureInfo } from "../utils/recalculation.utils";
import { useScaleT } from "../utils/useRecalculationT";

interface RunFailureNoticeProps {
  runId: string;
  errorCode?: string | null;
  errorMessage?: string | null;
  attempts?: number;
  onRetry?: () => void;
  retrying?: boolean;
}

export function RunFailureNotice({ runId, errorCode, errorMessage, attempts, onRetry, retrying = false }: RunFailureNoticeProps) {
  const t = useScaleT();
  const info = runFailureInfo(t, errorCode);

  return (
    <div
      role="alert"
      className="mx-5 mb-5 rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] p-3 text-[12px] text-[#c24a3a]"
    >
      <div className="font-semibold">{info.title}</div>
      <div className="mt-1 text-[var(--color-text-secondary)]">{info.hint}</div>
      {errorMessage ? <div className="mt-1.5 break-words text-[11.5px]">{errorMessage}</div> : null}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-[var(--color-text-muted)]">
        {errorCode ? <span className="font-mono">{errorCode}</span> : null}
        {attempts && attempts > 1 ? (
          <span>{t("scale.failure.attempts", "Tried {{count}} times", { count: attempts })}</span>
        ) : null}
        <span className="font-mono">{t("scale.failure.runId", "Run {{id}}", { id: runId.slice(0, 8) })}</span>
        {info.retry && onRetry ? (
          <Button size="sm" variant="secondary" disabled={retrying} onClick={onRetry}>
            {t("scale.failure.runAgain", "Run again")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
