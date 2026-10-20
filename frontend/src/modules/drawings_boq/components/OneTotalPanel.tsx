import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { PdfTakeoffStats } from "../types/drawings-boq.types";
import { formatPrecise } from "../utils/drawings-boq.utils";
import { decisionWords, kindWords, matchWords, oneTotalReasonWords, oneTotalView } from "../utils/oneTotal";
import { ruleKindOf } from "../utils/oneTotalRules";
import { OneTotalRuleButtons } from "./OneTotalRuleButtons";
import { OneTotalRulesList } from "./OneTotalRulesList";

const TITLE = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const NOTE = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)]";
const WARN = "rounded-[8px] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]";
const TH = "px-2 py-1.5 text-left text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const TD = "px-2 py-1.5 font-mono text-[12px] text-[var(--color-text-primary)]";

function Cell({ label, value, testId, tone }: { label: string; value: ReactNode; testId: string; tone?: "gold" }) {
  return (
    <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3" data-testid={testId}>
      <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{label}</div>
      <div className={`mt-1.5 font-mono text-[15px] font-semibold ${tone === "gold" ? "text-[var(--color-warning)]" : "text-[var(--color-text-primary)]"}`}>{value}</div>
    </div>
  );
}

export function OneTotalPanel({ takeoff, projectId }: { takeoff: PdfTakeoffStats | null | undefined; projectId?: string }) {
  const { t } = useTranslation();
  const v = oneTotalView(takeoff);
  if (!v) return null;
  if (!v.ran) {
    return (
      <div className={NOTE} data-testid="one-total-not-run">
        {t("boq.oneTotal.notRun", "The model and the drawings were not set against each other member by member.")} {oneTotalReasonWords(v.reason)}
      </div>
    );
  }
  return (
    <div className="space-y-3" data-testid="one-total">
      <div className={TITLE}>{t("boq.oneTotal.title", "One total: the model and the drawings")}</div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <Cell testId="one-total-complete" label={t("boq.oneTotal.complete", "Marks found whole in both")} value={v.complete} />
        <Cell testId="one-total-partial" label={t("boq.oneTotal.partial", "Found in part")} value={v.partial} tone={v.partial > 0 ? "gold" : undefined} />
        <Cell testId="one-total-conflicts" label={t("boq.oneTotal.conflicts", "Disagreements")} value={v.conflictsTotal} tone={v.conflictsTotal > 0 ? "gold" : undefined} />
        <Cell testId="one-total-drawing-only" label={t("boq.oneTotal.drawingOnly", "Only in the drawings")} value={v.drawingOnlyMarks} />
        <Cell testId="one-total-model-only" label={t("boq.oneTotal.modelOnly", "Only in the model")} value={v.modelOnlyMembers} />
      </div>
      <div className={NOTE} data-testid="one-total-basis">
        {t(
          "boq.oneTotal.basis",
          "A member of a drawing and a member of the model are the same member when they are the same kind, on the same storey, and agree by mark or by place. Each member is counted once: where both have it, one source is kept.",
        )}{" "}
        {t("boq.oneTotal.prefer", { defaultValue: "Kept when both have it: {{who}}.", who: v.prefer })}
        {v.positionToleranceMm !== null ? ` ${t("boq.oneTotal.tolerance", { defaultValue: "Same place means within {{mm}} mm once the drawing is placed on the model.", mm: v.positionToleranceMm })}` : ""}
      </div>

      {v.kinds.length > 0 ? (
        <div className="overflow-x-auto" data-testid="one-total-kinds">
          <table className="w-full min-w-[520px] border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className={TH}>{t("boq.oneTotal.kind", "Kind")}</th>
                <th className={TH}>{t("boq.oneTotal.fromModel", "Kept from the model (m³)")}</th>
                <th className={TH}>{t("boq.oneTotal.fromDrawing", "Kept from the drawings (m³)")}</th>
                <th className={TH}>{t("boq.oneTotal.total", "Total (m³)")}</th>
                <th className={TH}>{t("boq.oneTotal.range", "Range (m³)")}</th>
              </tr>
            </thead>
            <tbody>
              {v.kinds.map((k) => (
                <tr key={k.kind} className="border-b border-[var(--color-border)]" data-testid={`one-total-kind-${k.kind}`}>
                  <td className={TD}>{t(`boq.oneTotal.kinds.${k.kind}`, k.label)}</td>
                  <td className={TD}>{formatPrecise(k.modelM3, 3)}</td>
                  <td className={TD}>{formatPrecise(k.drawingM3, 3)}</td>
                  <td className={`${TD} font-semibold`}>{formatPrecise(k.totalM3, 3)}</td>
                  <td className={TD}>
                    {formatPrecise(k.lowM3, 3)} – {formatPrecise(k.highM3, 3)}
                    {k.bounded ? "" : ` ${t("boq.oneTotal.open", "(some rows have no bound)")}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">
            {t("boq.oneTotal.rangeNote", "The range adds the ranges of the rows kept, and reaches the other source's quantity where the two disagree.")}
          </p>
        </div>
      ) : null}

      {v.conflicts.length > 0 ? (
        <div className="space-y-1.5" data-testid="one-total-conflict-list">
          <div className={TITLE}>{t("boq.oneTotal.conflictTitle", "Where the model and the drawings disagree")}</div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className={TH}>{t("boq.oneTotal.mark", "Mark")}</th>
                  <th className={TH}>{t("boq.oneTotal.members", "Members")}</th>
                  <th className={TH}>{t("boq.oneTotal.drawingQty", "Drawing (m³)")}</th>
                  <th className={TH}>{t("boq.oneTotal.modelQty", "Model (m³)")}</th>
                  <th className={TH}>{t("boq.oneTotal.used", "Used")}</th>
                  <th className={TH}>{t("boq.oneTotal.why", "Why")}</th>
                  <th className={TH}>{t("boq.oneTotal.choose", "Which counts")}</th>
                </tr>
              </thead>
              <tbody>
                {v.conflicts.map((c) => (
                  <tr key={c.measurement_id} className="border-b border-[var(--color-border)] align-top" data-testid={`one-total-conflict-${c.measurement_id}`}>
                    <td className={TD}>
                      {c.tag ?? "—"} <span className="text-[var(--color-text-muted)]">{t(`boq.oneTotal.kinds.${c.category}`, kindWords(c.category))}</span>
                    </td>
                    <td className={TD}>
                      {c.matched} / {c.members}
                      {c.by ? <span className="block text-[10px] text-[var(--color-text-muted)]">{matchWords(c.by)}</span> : null}
                    </td>
                    <td className={TD}>{formatPrecise(c.drawing_m3, 3)}</td>
                    <td className={TD}>
                      {c.model_m3 !== null ? formatPrecise(c.model_m3, 3) : "—"}
                      {c.difference_pct !== null ? <span className="block text-[10px] text-[var(--color-text-muted)]">{Number(c.difference_pct) > 0 ? "+" : ""}{c.difference_pct}%</span> : null}
                    </td>
                    <td className={TD}>{c.used === "MODEL" ? t("boq.oneTotal.usedModel", "Model") : c.used === "BOTH" ? t("boq.oneTotal.usedBoth", "Both") : t("boq.oneTotal.usedDrawing", "Drawing")}</td>
                    <td className="px-2 py-1.5 text-[12px] text-[var(--color-text-secondary)]">
                      {decisionWords(c.reason)}
                      {c.size_differs ? ` ${t("boq.oneTotal.sizeDiffers", "The sizes differ.")}` : ""}
                    </td>
                    <td className="px-2 py-1.5">
                      <OneTotalRuleButtons projectId={projectId} kind={ruleKindOf(c.category)} mark={c.tag} levelName={c.level_name} used={c.used} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {v.decisions.length > 0 && projectId ? (
        <details data-testid="one-total-decisions">
          <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-text-primary)]">
            {t("boq.oneTotal.allDecisions", { defaultValue: "Every member decided ({{n}}): choose which source counts", n: v.decisions.length })}
          </summary>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full min-w-[560px] border-collapse">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className={TH}>{t("boq.oneTotal.mark", "Mark")}</th>
                  <th className={TH}>{t("boq.oneTotal.storey", "Storey")}</th>
                  <th className={TH}>{t("boq.oneTotal.used", "Used")}</th>
                  <th className={TH}>{t("boq.oneTotal.choose", "Which counts")}</th>
                </tr>
              </thead>
              <tbody>
                {v.decisions.map((c) => (
                  <tr key={c.measurement_id} className="border-b border-[var(--color-border)] align-top" data-testid={`one-total-decision-${c.measurement_id}`}>
                    <td className={TD}>{c.tag ?? "—"} <span className="text-[var(--color-text-muted)]">{t(`boq.oneTotal.kinds.${c.category}`, kindWords(c.category))}</span></td>
                    <td className={TD}>{c.level_name ?? "—"}</td>
                    <td className={TD}>{c.used === "MODEL" ? t("boq.oneTotal.usedModel", "Model") : c.used === "BOTH" ? t("boq.oneTotal.usedBoth", "Both") : t("boq.oneTotal.usedDrawing", "Drawing")}{c.rule ? <span className="block text-[10px] text-[var(--color-text-muted)]">{t("boq.oneTotal.byChoice", "by your choice")}</span> : null}</td>
                    <td className="px-2 py-1.5"><OneTotalRuleButtons projectId={projectId} kind={ruleKindOf(c.category)} mark={c.tag} levelName={c.level_name} used={c.used} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
      {v.rulesGiven > 0 ? (
        <div className={NOTE} data-testid="one-total-rules-applied">
          {t("boq.oneTotal.rulesApplied", { defaultValue: "Your choices: {{given}} given to this run, {{applied}} applied to a member.", given: v.rulesGiven, applied: v.rulesApplied })}
        </div>
      ) : null}
      <OneTotalRulesList projectId={projectId} />

      {v.notTrusted.length > 0 ? (
        <div className={WARN} data-testid="one-total-not-trusted">
          {t("boq.oneTotal.notTrusted", "Not matched; the model was kept and the drawing set aside for these:")}{" "}
          {v.notTrusted.map((n) => `${n.kind} (${n.matched} of ${Math.min(n.drawingMembers, n.modelMembers)} found a partner)`).join("; ")}.{" "}
          {t("boq.oneTotal.notTrustedHelp", "Give the drawing's views a confirmed place, or give the members the same marks in both.")}
        </div>
      ) : null}

      {v.drawingOnly.length > 0 ? (
        <div className="space-y-1" data-testid="one-total-drawing-only-list">
          <div className={TITLE}>{t("boq.oneTotal.drawingOnlyTitle", "Only in the drawings (counted)")}</div>
          <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
            {v.drawingOnly.map((d, i) => (
              <li key={`${d.tag}-${i}`}>
                <span className="font-mono font-semibold text-[var(--color-text-primary)]">{d.tag}</span> {d.kind} × {d.members} · {formatPrecise(d.m3, 3)} m³ — {d.why}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {v.modelOnly.length > 0 ? (
        <div className="space-y-1" data-testid="one-total-model-only-list">
          <div className={TITLE}>{t("boq.oneTotal.modelOnlyTitle", "Only in the model (kept)")}</div>
          <ul className="space-y-0.5 text-[12px] text-[var(--color-text-secondary)]">
            {v.modelOnly.slice(0, 25).map((m) => (
              <li key={m.elementId}>
                <span className="font-mono font-semibold text-[var(--color-text-primary)]">{m.mark}</span> {m.kind} · {formatPrecise(m.m3, 3)} m³
              </li>
            ))}
          </ul>
          {v.modelOnly.length > 25 ? <p className="text-[11px] text-[var(--color-text-muted)]">{t("boq.oneTotal.more", { defaultValue: "and {{n}} more", n: v.modelOnly.length - 25 })}</p> : null}
        </div>
      ) : null}

      {v.alignments.length > 0 ? (
        <div className={NOTE} data-testid="one-total-alignment">
          {t("boq.oneTotal.alignment", "Placing the drawing on the model:")}{" "}
          {v.alignments.map((a) => (a.method === "VOTE" ? `${a.supporters} of ${a.compared} columns and footings agree` : "no agreed place, so names alone were used")).join("; ")}.
        </div>
      ) : null}
      {v.truncated ? <div className={NOTE}>{t("boq.oneTotal.truncated", "The lists above show the first 300 of each.")}</div> : null}
    </div>
  );
}
