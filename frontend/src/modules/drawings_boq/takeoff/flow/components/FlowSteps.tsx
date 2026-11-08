import { useRef } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import type { FlowStep } from "../types/flow.types";
import { STATE_TEXT, STATE_TONE, STEP_ORDER, STEP_TEXT } from "../utils/flow";

interface FlowStepsProps {
  projectId: string;
  steps: FlowStep[];
  next: string | null;
  busy: boolean;
  onUpload: (file: File) => void;
  onRead: () => void;
  onQuantities: () => void;
  onOpenBoq: () => void;
  onOpenReview: () => void;
}

export function FlowSteps({ projectId, steps, next, busy, onUpload, onRead, onQuantities, onOpenBoq, onOpenReview }: FlowStepsProps) {
  const { t } = useTranslation();
  const picker = useRef<HTMLInputElement>(null);
  const byKey = new Map(steps.map((s) => [s.key, s]));
  const action = (key: string, state: string) => {
    const label = "rounded-full border border-[var(--color-border)] px-3 py-1 text-[12.5px] font-semibold disabled:opacity-50";
    if (key === "upload") {
      return (
        <>
          <input ref={picker} type="file" accept="application/pdf" className="hidden" data-testid="flow-upload-input" onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); e.target.value = ""; }} />
          <button type="button" className={label} disabled={busy} onClick={() => picker.current?.click()} data-testid="flow-upload">{t("boq.flow.uploadPdf", "Add a PDF")}</button>
        </>
      );
    }
    if (key === "read") return <button type="button" className={label} disabled={busy || state === "RUNNING"} onClick={onRead} data-testid="flow-read">{state === "DONE" ? t("boq.flow.readAgain", "Read again") : t("boq.flow.read", "Read the drawings")}</button>;
    if (key === "quantities") return <button type="button" className={label} disabled={busy || state === "RUNNING"} onClick={onQuantities} data-testid="flow-quantities">{state === "DONE" ? t("boq.flow.calcAgain", "Calculate again") : t("boq.flow.calc", "Calculate")}</button>;
    if (key === "review") return <Link to={`/takeoff-review/${projectId}`} className={label} onClick={onOpenReview} data-testid="flow-review">{t("boq.flow.openReview", "Open the review list")}</Link>;
    if (key === "boq") return <button type="button" className={label} disabled={state === "OPEN"} onClick={onOpenBoq} data-testid="flow-boq">{t("boq.flow.openBoq", "Show the priced BOQ")}</button>;
    return null;
  };
  return (
    <ol className="space-y-2" data-testid="flow-steps">
      {STEP_ORDER.map((key, n) => {
        const step = byKey.get(key);
        if (!step) return null;
        return (
          <li key={key} className={`flex flex-wrap items-center gap-3 rounded-[10px] border px-3 py-2 ${next === key ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"}`} data-testid={`flow-step-${key}`}>
            <span className="w-5 text-[12px] font-mono text-[var(--color-text-muted)]">{n + 1}</span>
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-semibold">{t(`boq.flow.step.${key}`, STEP_TEXT[key])}</div>
              {step.detail ? <div className="text-[12px] text-[var(--color-text-muted)]">{step.detail}</div> : null}
            </div>
            <Badge tone={STATE_TONE[step.state]}>{STATE_TEXT[step.state]}</Badge>
            {action(key, step.state)}
          </li>
        );
      })}
    </ol>
  );
}
