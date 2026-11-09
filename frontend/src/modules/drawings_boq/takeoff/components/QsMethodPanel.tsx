import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, useToast } from "../../../organizations/components/OrganizationUi";
import { useChooseQsMethod, useQsMethods } from "../hooks/useCompanyConventions";
import type { QsMethodProfile } from "../types/qsMethods.types";
import { takeoffErrorMessage } from "../utils/errors";
import { ASPECT_TEXT, STATE_TEXT, STATE_TONE, byAspect, scopeText, summaryText, valueText } from "../utils/qsMethods";

interface Props {
  canManage: boolean;
}

export function QsMethodPanel({ canManage }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [showing, setShowing] = useState<string | null>(null);
  const q = useQsMethods(open);
  const choose = useChooseQsMethod();
  const data = q.data;
  const chosen = data?.profiles.find((p) => p.chosen) ?? null;

  function pick(profile: string | null) {
    choose.mutate({ profile }, {
      onSuccess: (r) => showToast({
        tone: "success",
        title: profile
          ? t("boq.takeoff.qsMethod.chosen", "Measuring the way {{qs}} does. {{n}} rules are in your rule book; sheets keep their old figures until they are read again.", { qs: data?.profiles.find((p) => p.id === profile)?.qs ?? "", n: r.written })
          : t("boq.takeoff.qsMethod.off", "Back to Trace's own method. {{n}} rules were taken out of your rule book.", { n: r.removed }),
        description: r.kept.length ? t("boq.takeoff.qsMethod.keptNote", "{{n}} figures you set yourself were kept.", { n: r.kept.length }) : undefined,
      }),
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.company.saveFailed", "Could not save"), description: takeoffErrorMessage(e) }),
    });
  }

  function card(p: QsMethodProfile) {
    const expanded = showing === p.id;
    return (
      <li key={p.id} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`qs-method-${p.id}`} data-chosen={p.chosen}>
        <div className="flex flex-wrap items-center gap-2">
          <span className="min-w-[10rem] flex-1 font-medium">{p.label}</span>
          {p.chosen ? <Badge tone="green">{t("boq.takeoff.qsMethod.inUse", "in use")}</Badge> : null}
          {p.unconfirmed ? <Badge tone="gold">{t("boq.takeoff.qsMethod.unconfirmed", "{{n}} not yet confirmed by {{qs}}", { n: p.unconfirmed, qs: p.qs })}</Badge> : null}
          <Button size="sm" variant="ghost" onClick={() => setShowing(expanded ? null : p.id)} data-testid={`qs-method-show-${p.id}`}>
            {expanded ? t("boq.takeoff.company.hide", "Hide") : t("boq.takeoff.qsMethod.details", "See every method")}
          </Button>
          {canManage && !p.chosen ? (
            <Button size="sm" variant="primary" disabled={choose.isPending} onClick={() => pick(p.id)} data-testid={`qs-method-use-${p.id}`}>
              {t("boq.takeoff.qsMethod.use", "Measure the way {{qs}} does", { qs: p.qs })}
            </Button>
          ) : null}
        </div>
        <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{summaryText(p)}</p>
        {expanded ? (
          <div className="mt-2 space-y-2">
            {byAspect(p.methods).map(([aspect, rows]) => (
              <div key={aspect}>
                <h5 className="text-[11.5px] font-semibold text-[var(--color-text-secondary)]">{t(`boq.takeoff.qsMethod.aspect.${aspect}`, ASPECT_TEXT[aspect])}</h5>
                <ul className="space-y-1">
                  {rows.map((m) => (
                    <li key={m.id} className="rounded-[6px] bg-[var(--color-surface-muted)] p-2" data-testid={`qs-method-row-${m.id}`} data-state={m.state}>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="min-w-[8rem] flex-1">{m.says}</span>
                        <span className="font-medium">{valueText(m.value)}{scopeText(m.scope)}</span>
                        <Badge tone={STATE_TONE[m.state]}>{t(`boq.takeoff.qsMethod.state.${m.state}`, STATE_TEXT[m.state])}</Badge>
                      </div>
                      <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                        {m.item} · {m.source}{m.confirmed ? "" : ` · ${t("boq.takeoff.qsMethod.fromWorkbook", "read from his workbook, not confirmed")}`}
                        {m.state === "WOULD_CHANGE" ? ` · ${t("boq.takeoff.qsMethod.traceDoes", "Trace now: {{v}}", { v: valueText(m.trace_value) })}` : ""}
                        {m.state === "YOURS" ? ` · ${t("boq.takeoff.qsMethod.yourFigure", "yours: {{v}}", { v: valueText(m.held_value) })}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : null}
      </li>
    );
  }

  return (
    <div className="space-y-2" data-testid="qs-method-panel">
      <button type="button" className="flex w-full items-center gap-2 text-left" aria-expanded={open} onClick={() => setOpen(!open)} data-testid="qs-method-toggle">
        <h4 className="text-[11.5px] font-semibold text-[var(--color-text-secondary)]">{t("boq.takeoff.qsMethod.title", "How quantities are measured")}</h4>
        {data ? <Badge tone={chosen ? "green" : "slate"}>{chosen ? chosen.label : t("boq.takeoff.qsMethod.traceDefault", "Trace's own method")}</Badge> : null}
        <span className="ml-auto text-[11px] text-[var(--color-text-muted)]">{open ? t("boq.takeoff.company.hide", "Hide") : t("boq.takeoff.company.show", "Show")}</span>
      </button>
      {open ? (
        <div className="space-y-2">
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.takeoff.qsMethod.help", "A quantity surveyor's way of measuring (what he deducts, which faces he counts, his laps and wastage) changes the quantity without changing what the drawing says. Choosing it puts his rules into your rule book, each with where it came from. A figure you set yourself is never overwritten, and you can go back to Trace's own method at any time.")}
          </p>
          {q.isLoading ? <p>{t("boq.takeoff.company.loading", "Loading…")}</p> : null}
          {q.isError ? <p className="text-[var(--color-danger)]">{takeoffErrorMessage(q.error)}</p> : null}
          {data ? (
            <>
              <ul className="space-y-1">{data.profiles.map(card)}</ul>
              {canManage && chosen ? (
                <Button size="sm" variant="secondary" disabled={choose.isPending} onClick={() => pick(null)} data-testid="qs-method-off">
                  {t("boq.takeoff.qsMethod.useTrace", "Go back to Trace's own method")}
                </Button>
              ) : null}
              {data.open_questions.length ? (
                <div data-testid="qs-method-open">
                  <h5 className="text-[11.5px] font-semibold text-[var(--color-text-secondary)]">{t("boq.takeoff.qsMethod.openTitle", "Not answered yet")}</h5>
                  <p className="text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.qsMethod.openHelp", "Where the QS has not said how he measures, Trace uses its own method and says so. These are the questions still to put to him.")}</p>
                  <ul className="mt-1 space-y-1">
                    {data.open_questions.map((o) => (
                      <li key={o.id} className="rounded-[6px] border border-dashed border-[var(--color-border)] p-2" data-testid={`qs-open-${o.id}`}>
                        <span className="font-medium">{o.item}</span> · {o.question}
                        <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">
                          {t("boq.takeoff.qsMethod.traceUses", "Trace uses: {{v}}", { v: o.trace })}
                          {o.standard ? ` · ${t("boq.takeoff.qsMethod.standardSays", "IS 1200: {{v}}", { v: o.standard })}` : ""}
                          {o.asked ? ` · ${t("boq.takeoff.qsMethod.askedOn", "asked {{d}}", { d: o.asked })}` : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
