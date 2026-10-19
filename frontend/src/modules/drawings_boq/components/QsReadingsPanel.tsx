import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useQsAnswers } from "../hooks/useQsReadings";
import { QS_STATUS_LABEL, QS_STATUS_TONE, qsSectionGroups, qsWaitingCount } from "../utils/qsReadings";
import type { QsAnswer } from "../api/qsReadings.api";

function AnswerRow({ a }: { a: QsAnswer }) {
  const { t } = useTranslation();
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] font-bold text-[var(--color-text-muted)]">{a.id}</span>
        <span className="text-[12px] font-semibold text-[var(--color-text-primary)]">{a.topic}</span>
        <Badge tone={QS_STATUS_TONE[a.status]}>{t(`boq.qs.status.${a.status}`, QS_STATUS_LABEL[a.status])}</Badge>
      </div>
      <p className="mt-1.5 text-[11px] leading-snug text-[var(--color-text-muted)]">{a.question}</p>
      <p className="mt-1.5 text-[12px] leading-snug text-[var(--color-text-primary)]">{a.answer}</p>
      <p className="mt-1.5 text-[11px] leading-snug text-[var(--color-text-secondary)]">
        <span className="font-semibold">{t("boq.qs.whatChanged", "What the software does")}: </span>
        {a.applied}
      </p>
      {a.confirm ? (
        <p className="mt-1.5 text-[11px] leading-snug text-[var(--color-warning)]">
          <span className="font-semibold">{t("boq.qs.toConfirm", "Still to settle")}: </span>
          {a.confirm}
        </p>
      ) : null}
      {a.workbook ? (
        <p className="mt-1.5 font-mono text-[10px] leading-snug text-[var(--color-text-muted)]">
          {t("boq.qs.workbook", "His workbook")}: {a.workbook}
        </p>
      ) : null}
    </li>
  );
}

export function QsAnswersPanel() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const query = useQsAnswers();
  const data = query.data;
  if (query.isLoading || query.isError || !data) return null;
  const waiting = qsWaitingCount(data);
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.qs.eyebrow", "Answers from the QS")}
        title={t("boq.qs.title", "How the QS measures this plot")}
        description={t(
          "boq.qs.description",
          "The values he gave are used when your project has none of its own. Anything he has not answered is listed here and is never assumed.",
        )}
        action={
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[12px] font-semibold text-[var(--color-text-primary)]"
          >
            {open ? t("boq.qs.hide", "Hide") : t("boq.qs.show", "Show the answers")}
            {waiting > 0 ? ` (${waiting} ${t("boq.qs.waiting", "to settle")})` : ""}
          </button>
        }
      />
      {open ? (
        <div className="space-y-4 border-t border-[var(--color-border)] p-5">
          {qsSectionGroups(data).map((g) => (
            <section key={g.key}>
              <h4 className="text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                {g.key} · {g.title}
              </h4>
              <ul className="mt-2 space-y-2">
                {g.answers.map((a) => (
                  <AnswerRow key={a.id} a={a} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : null}
    </Panel>
  );
}
