import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon, Panel, PanelHeader } from "./OrganizationUi";
import { useOnboardingStatus } from "../hooks/useOnboardingStatus";

function getDismissalKey(organizationId: string): string {
  return `trace_onboarding_dismissed_${organizationId}`;
}

interface OnboardingChecklistProps {
  organizationId: string;
}

export function OnboardingChecklist({ organizationId }: OnboardingChecklistProps) {
  const status = useOnboardingStatus();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setDismissed(window.localStorage.getItem(getDismissalKey(organizationId)) === "true");
  }, [organizationId]);

  if (status.isLoading || status.isComplete || dismissed) {
    return null;
  }

  function dismiss() {
    window.localStorage.setItem(getDismissalKey(organizationId), "true");
    setDismissed(true);
  }

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="GET STARTED"
        title="Set up your workspace"
        description={`${status.completedCount} of ${status.totalCount} steps complete — this only takes a few minutes.`}
        action={
          <button
            type="button"
            onClick={dismiss}
            aria-label="Hide setup checklist"
            className="flex h-8 w-8 items-center justify-center rounded-[8px] text-[var(--color-text-secondary)] outline-none transition hover:bg-[var(--color-surface-muted)] focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)]"
          >
            <Icon name="x" size={15} />
          </button>
        }
      />

      <div className="divide-y divide-[var(--color-border)]">
        {status.steps.map((step) => {
          const rowContent = (
            <>
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 ${
                  step.done
                    ? "border-[var(--color-success)] bg-[var(--color-success)] text-white"
                    : "border-[var(--color-border-strong)] text-transparent"
                }`}
              >
                {step.done ? <Icon name="check" size={12} strokeWidth={2.6} /> : null}
              </span>

              <span className="min-w-0 flex-1">
                <span
                  className={`block text-[13.5px] font-medium ${
                    step.done
                      ? "text-[var(--color-text-muted)] line-through"
                      : step.locked
                        ? "text-[var(--color-text-muted)]"
                        : "text-[var(--color-text-primary)]"
                  }`}
                >
                  {step.label}
                </span>
                {step.locked && !step.done ? (
                  <span className="block text-[11.5px] text-[var(--color-text-muted)]">{step.lockedHint}</span>
                ) : null}
              </span>

              {!step.done && !step.locked ? (
                <Icon name="arrow" size={13} className="shrink-0 text-[var(--color-text-muted)]" />
              ) : null}
            </>
          );

          if (step.done || step.locked) {
            return (
              <div key={step.key} className="flex items-center gap-3 px-5 py-3.5 sm:px-6">
                {rowContent}
              </div>
            );
          }

          return (
            <Link
              key={step.key}
              to={step.to}
              className="flex items-center gap-3 px-5 py-3.5 outline-none transition hover:bg-[var(--color-surface-muted)] focus-visible:bg-[var(--color-surface-muted)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-trace-gold)] sm:px-6"
            >
              {rowContent}
            </Link>
          );
        })}
      </div>
    </Panel>
  );
}