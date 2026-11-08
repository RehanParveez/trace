import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../../organizations/components/OrganizationUi";
import type { ReviewAction, ReviewRow } from "../types/review.types";
import { KIND_TEXT, lineQuantity, moneyText, SOURCE_TEXT, SOURCE_TONE } from "../utils/review";
import { ReviewCrop } from "./ReviewCrop";

interface Props {
  row: ReviewRow;
  canEdit: boolean;
  busy: boolean;
  onAct: (action: ReviewAction["action"] | "withdraw", value: string | null) => void;
}

const label = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

function CorrectBox({ spec, busy, onSend }: { spec: ReviewAction; busy: boolean; onSend: (value: string) => void }) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  return (
    <div className="flex flex-wrap items-center gap-2">
      {spec.choices.length > 0 ? (
        <select className="min-h-9 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-[13px]" value={value} onChange={(e) => setValue(e.target.value)} data-testid="review-choice">
          <option value="">{t("boq.review.pick", "Pick a value")}</option>
          {spec.choices.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      ) : (
        <input className="min-h-9 w-40 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-[13px]" value={value} onChange={(e) => setValue(e.target.value)} placeholder={t("boq.review.value", "Value")} data-testid="review-value" />
      )}
      <Button size="sm" disabled={busy || value.trim() === ""} onClick={() => onSend(value.trim())}>{t("boq.review.correct", "Correct")}</Button>
    </div>
  );
}

export function ReviewPanel({ row, canEdit, busy, onAct }: Props) {
  const { t } = useTranslation();
  const fixed = row.actions.filter((a) => a.action !== "correct");
  const correct = row.actions.find((a) => a.action === "correct");
  return (
    <aside className="space-y-4 rounded-[8px] border border-[var(--color-border)] p-4" data-testid="review-panel">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="slate">{KIND_TEXT[row.kind]}</Badge>
        <Badge tone={SOURCE_TONE[row.source]}>{SOURCE_TEXT[row.source]}</Badge>
        {row.state === "DECIDED" ? <Badge tone="green">{t("boq.review.decided", "Decided")}</Badge> : null}
      </div>
      <div>
        <div className="text-[14px] font-semibold">{row.item}</div>
        <p className="mt-1 text-[12.5px] text-[var(--color-text-secondary)]">{row.prompt}</p>
      </div>
      <ReviewCrop row={row} />
      {row.quote ? (
        <div>
          <div className={label}>{t("boq.review.quote", "Quoted from the sheet")}</div>
          <p className="mt-1 whitespace-pre-wrap rounded-[6px] bg-[var(--color-surface-muted)] p-2 font-mono text-[12px]" data-testid="review-quote">{row.quote}</p>
        </div>
      ) : null}
      <div>
        <div className={label}>{t("boq.review.changes", "What it changes in the BOQ")}</div>
        <div className="mt-1 text-[13px] font-semibold" data-testid="review-money">{moneyText(row.effect_rs)}</div>
        {row.lines.length === 0 ? (
          <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">{t("boq.review.noLines", "No BOQ line is recorded as using this yet.")}</p>
        ) : (
          <ul className="mt-1 max-h-40 space-y-0.5 overflow-auto text-[12px]">
            {row.lines.map((l) => <li key={`${l.element}-${l.floor}`}><span className="font-mono font-semibold">{l.element}</span> {l.floor !== "ALL" ? l.floor : ""} {l.name}: {lineQuantity(l)}</li>)}
          </ul>
        )}
        {row.unquantified > 0 ? <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{t("boq.review.unquantified", "{{n}} line(s) hold no quantity until this is decided.", { n: row.unquantified })}</p> : null}
      </div>
      {row.decision ? (
        <p className="text-[12px] text-[var(--color-text-secondary)]" data-testid="review-decision">
          {t("boq.review.decision", "Decided: {{action}}{{value}}", { action: row.decision.action, value: row.decision.value ? ` (${row.decision.value})` : "" })}
        </p>
      ) : null}
      {canEdit ? (
        <div className="space-y-2 border-t border-[var(--color-border)] pt-3">
          <div className="flex flex-wrap gap-2">
            {fixed.map((a) => (
              <Button key={a.action} size="sm" variant={a.action === "reject" ? "danger" : "primary"} disabled={busy} onClick={() => onAct(a.action, a.value)} data-testid={`review-${a.action}`}>
                {a.action === "accept" ? t("boq.review.accept", "Accept") : t("boq.review.reject", "Reject")}
              </Button>
            ))}
            {row.decision ? <Button size="sm" variant="ghost" disabled={busy} onClick={() => onAct("withdraw", null)}>{t("boq.review.withdraw", "Take the decision back")}</Button> : null}
          </div>
          {correct ? <CorrectBox spec={correct} busy={busy} onSend={(v) => onAct("correct", v)} /> : null}
        </div>
      ) : null}
    </aside>
  );
}
