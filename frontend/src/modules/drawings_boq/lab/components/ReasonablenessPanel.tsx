import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../../organizations/components/OrganizationUi";
import { useReasonableness } from "../hooks/useRunCompare";
import type { CheckStatus, ReasonCheck } from "../types/reasonableness.types";

const TONE: Record<CheckStatus, "green" | "red" | "slate"> = { PASS: "green", WARN: "red", INFO: "slate" };
const STATUS_TEXT: Record<CheckStatus, string> = { PASS: "Fits", WARN: "Look at this", INFO: "Not judged" };

function figure(v: number): string {
  const rounded = Math.abs(v) >= 100 ? Math.round(v) : Math.round(v * 100) / 100;
  return rounded.toLocaleString("en-US");
}

function CheckRow({ check }: { check: ReasonCheck }) {
  const { t } = useTranslation();
  return (
    <li className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`reason-${check.code}`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={TONE[check.status]}>{t(`drawings.reason.status.${check.status}`, STATUS_TEXT[check.status])}</Badge>
        <span className="font-semibold text-[var(--color-text-primary)]">{t(`drawings.reason.code.${check.code}`, check.label)}</span>
        {check.value !== null ? (
          <span className="font-mono text-[var(--color-text-primary)]">
            {figure(check.value)} {check.unit}
          </span>
        ) : null}
        {check.low !== null && check.high !== null ? (
          <span className="text-[var(--color-text-muted)]">{t("drawings.reason.usual", "usual {{low}} to {{high}}", { low: figure(check.low), high: figure(check.high) })}</span>
        ) : null}
      </div>
      <p className="mt-1 text-[var(--color-text-secondary)]">{check.message}</p>
      {check.inputs.length > 0 ? (
        <p className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]">{check.inputs.map((i) => `${i.label} ${figure(i.quantity)} ${i.unit}`).join(" · ")}</p>
      ) : null}
    </li>
  );
}

export function ReasonablenessPanel({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const q = useReasonableness(runId);
  if (q.isLoading) return <LoadingState label={t("drawings.reason.loading", "Checking that the quantities fit each other…")} />;
  if (q.isError) return <ErrorState title={t("drawings.reason.loadError", "The checks could not be run.")} onRetry={() => void q.refetch()} />;
  const d = q.data;
  if (!d || (d.checks.length === 0 && d.figures.length === 0)) {
    return <EmptyState icon="building" title={t("drawings.reason.empty", "This run has no quantities to check yet.")} description="" />;
  }
  return (
    <div className="space-y-3 px-4 py-3 text-[12.5px]" data-testid="reasonableness">
      <p className="text-[var(--color-text-muted)]">
        {t("drawings.reason.intro", "These checks need no bill. Each sets two figures of this run against each other: steel with concrete, plaster with brick work, excavation with what goes in it.")}
      </p>
      <p className="font-semibold text-[var(--color-text-primary)]" data-testid="reason-summary">
        {t("drawings.reason.summary", "{{warn}} to look at, {{pass}} fit, {{info}} not judged.", { warn: d.warnings, pass: d.passed, info: d.info })}
      </p>
      <ul className="list-none space-y-2 pl-0">
        {d.checks.map((c) => (
          <CheckRow key={c.code} check={c} />
        ))}
      </ul>
      {d.ungrouped_rows > 0 ? (
        <p className="text-[var(--color-warning)]" data-testid="reason-ungrouped">
          {t("drawings.reason.ungrouped", "{{n}} rows of the run belong to no group above, so the checks may be incomplete.", { n: d.ungrouped_rows })}
        </p>
      ) : null}
      {d.figures.length > 0 ? (
        <details>
          <summary className="cursor-pointer text-[var(--color-text-muted)]">{t("drawings.reason.figures", "The figures used")}</summary>
          <ul className="mt-1 list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
            {d.figures.map((f) => (
              <li key={f.key}>
                {f.label}: {figure(f.quantity)} {f.unit} ({f.rows})
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <p className="text-[11.5px] text-[var(--color-text-muted)]">{d.note}</p>
    </div>
  );
}
