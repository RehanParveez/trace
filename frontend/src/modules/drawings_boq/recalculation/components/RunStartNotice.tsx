import { Link } from "react-router-dom";
import { Button } from "../../../organizations/components/OrganizationUi";
import type { StartRunError } from "../utils/recalculation.utils";
import { useScaleT } from "../utils/useRecalculationT";

interface RunStartNoticeProps {
  error: StartRunError;
  onRetry?: () => void;
  onDismiss?: () => void;
  retrying?: boolean;
}

export function RunStartNotice({ error, onRetry, onDismiss, retrying = false }: RunStartNoticeProps) {
  const t = useScaleT();

  const guidance: Record<string, { title: string; hint: string }> = {
    concurrency: {
      title: t("scale.start.concurrency.title", "Your company has enough calculations running already"),
      hint: t("scale.start.concurrency.hint", "Wait for one of them to finish, then start this one. Nothing was lost."),
    },
    rate: {
      title: t("scale.start.rate.title", "Too many calculations started in a short time"),
      hint: t("scale.start.rate.hint", "Give it a few minutes and try again. The usage panel shows when the window resets."),
    },
    in_progress: {
      title: t("scale.start.inProgress.title", "This project is already being calculated"),
      hint: t("scale.start.inProgress.hint", "A run for this project is still going. Open it to follow its progress, or try again when it ends."),
    },
    quota: {
      title: t("scale.start.quota.title", "Your plan has no calculation runs left"),
      hint: t("scale.start.quota.hint", "The runs included in your plan for this period are used up. Review your subscription to add more."),
    },
    other: {
      title: t("scale.start.other.title", "The calculation could not be started"),
      hint: "",
    },
  };
  const g = guidance[error.kind] ?? guidance.other;

  return (
    <div
      role="alert"
      className="rounded-[8px] border border-[var(--color-warning)]/40 bg-[var(--color-warning-bg)] p-3 text-[12px] text-[var(--color-text-primary)]"
    >
      <div className="font-semibold">{g.title}</div>
      {g.hint ? <div className="mt-1 text-[var(--color-text-secondary)]">{g.hint}</div> : null}
      {error.message ? (
        <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">{error.message}</div>
      ) : null}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {error.retryable && onRetry ? (
          <Button size="sm" variant="secondary" disabled={retrying} onClick={onRetry}>
            {t("scale.start.tryAgain", "Try again")}
          </Button>
        ) : null}
        {error.kind === "quota" ? (
          <Link
            to="/app/subscription"
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[11px] font-semibold text-[var(--color-text-primary)]"
          >
            {t("scale.start.viewSubscription", "View subscription")}
          </Link>
        ) : null}
        {onDismiss ? (
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            {t("scale.start.dismiss", "Dismiss")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
