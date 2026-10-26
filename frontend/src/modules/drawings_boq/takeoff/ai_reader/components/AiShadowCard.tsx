import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { aiShadowApi } from "../api/aiShadow.api";
import { useAiShadow, useRunAiShadow } from "../hooks/useAiShadow";
import type { ShadowAgreement, ShadowReadItem } from "../types/aiShadow.types";

const FACT_LABEL: Record<string, string> = { discipline: "Discipline", sheet_type: "Sheet type", floor: "Floor", title: "Title", sheet_no: "Sheet number" };
const ORDER: ShadowAgreement[] = ["AGREE", "DISAGREE", "AI_ONLY", "RULE_ONLY"];
const WORD: Record<ShadowAgreement, string> = { AGREE: "agree", DISAGREE: "differ", AI_ONLY: "AI only", RULE_ONLY: "rules only" };
const TONE: Record<ShadowAgreement, "green" | "red" | "gold" | "slate"> = { AGREE: "green", DISAGREE: "red", AI_ONLY: "gold", RULE_ONLY: "slate" };

function CropView({ readId }: { readId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let made: string | null = null;
    let alive = true;
    aiShadowApi.crop(readId).then((blob) => {
      if (!alive) return;
      made = URL.createObjectURL(blob);
      setUrl(made);
    }).catch(() => alive && setFailed(true));
    return () => {
      alive = false;
      if (made) URL.revokeObjectURL(made);
    };
  }, [readId]);
  if (failed) return <p className="text-[11px] text-[var(--color-text-muted)]">The picture could not be loaded.</p>;
  if (!url) return <p className="text-[11px] text-[var(--color-text-muted)]">Loading the picture the AI saw...</p>;
  return <img src={url} alt="The title-block strips sent to the AI" className="mt-1 max-h-[320px] max-w-full rounded-[4px] border border-[var(--color-border)]" />;
}

function Row({ item }: { item: ShadowReadItem }) {
  const [open, setOpen] = useState(false);
  const differs = item.comparison.filter((c) => c.agreement !== "AGREE");
  return (
    <li className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`ai-shadow-${item.page_no}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">Page {item.page_no}</span>
        {item.status === "OK" ? ORDER.filter((k) => item.totals[k]).map((k) => <Badge key={k} tone={TONE[k]}>{item.totals[k]} {WORD[k]}</Badge>) : <Badge tone="red">{item.status === "FAILED" ? "not read" : "answer not usable"}</Badge>}
        <button type="button" className="ml-auto text-[11px] underline" onClick={() => setOpen((v) => !v)}>{open ? "Hide the picture" : "Show the picture"}</button>
      </div>
      {item.error ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{item.error}</p> : null}
      {differs.length ? (
        <ul className="mt-1 space-y-0.5 text-[11.5px]">
          {differs.map((c) => (
            <li key={c.fact_key}>{FACT_LABEL[c.fact_key] ?? c.fact_key}: rules {c.rule_value ?? "nothing"}, AI {c.ai_value ?? "nothing"}</li>
          ))}
        </ul>
      ) : null}
      {open ? <CropView readId={item.id} /> : null}
    </li>
  );
}

export function AiShadowCard({ drawingId, canEdit }: { drawingId: string | undefined; canEdit: boolean }) {
  const { t } = useTranslation();
  const q = useAiShadow(drawingId);
  const run = useRunAiShadow(drawingId);
  const d = q.data;
  if (!d || !d.enabled) return null;
  const pct = (k: string) => {
    const f = d.by_fact[k];
    const n = f ? ORDER.reduce((s, a) => s + f[a], 0) : 0;
    return n ? `${Math.round((100 * f.AGREE) / n)}% of ${n}` : "no reading yet";
  };
  return (
    <details className="rounded-[8px] border border-[var(--color-border)] p-3 text-[12px]" data-testid="ai-shadow">
      <summary className="cursor-pointer font-semibold">{t("takeoff.aiShadow.title", "AI second reader (measuring only)")} <span className="font-normal text-[var(--color-text-muted)]">{d.sheets_read} of {d.sheets_total} sheets read</span></summary>
      <p className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">{d.note}</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.keys(FACT_LABEL).map((k) => <Badge key={k} tone="slate">{FACT_LABEL[k]}: {pct(k)} agree</Badge>)}
      </div>
      {canEdit ? (
        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" className="rounded-[6px] border border-[var(--color-border)] px-2 py-1 text-[11.5px]" disabled={run.isPending} onClick={() => run.mutate({ mode: "WEAK", limit: 3 })}>
            {run.isPending ? "Reading..." : t("takeoff.aiShadow.weak", "Read the next 3 sheets the rules are unsure of")}
          </button>
          <button type="button" className="rounded-[6px] border border-[var(--color-border)] px-2 py-1 text-[11.5px]" disabled={run.isPending} onClick={() => run.mutate({ mode: "ALL", limit: 3 })}>
            {t("takeoff.aiShadow.all", "Read the next 3 sheets of any kind (to measure)")}
          </button>
        </div>
      ) : null}
      {run.error ? <p className="mt-1 text-[11.5px] text-[var(--color-danger,#b42318)]">The AI reading did not run. Check that AI is switched on for this company.</p> : null}
      {run.data ? <p className="mt-1 text-[11.5px]">{run.data.read} read, {run.data.failed} failed, {run.data.remaining} left to read.</p> : null}
      <ul className="mt-2 space-y-1.5">{d.items.map((i) => <Row key={i.id} item={i} />)}</ul>
    </details>
  );
}
