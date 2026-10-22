import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, useToast } from "../../../../organizations/components/OrganizationUi";
import { useDecideAgain, useDeleteSweep, useTuningPlan, useTuningRegistry, useTuningSweep, useTuningSweeps } from "../hooks/useTuning";
import type { Decisions, Ladder, Patch, SweepItem, TuningPlan, TuningRegistry } from "../types/tuning.types";
import { takeoffErrorMessage } from "../../utils/errors";
import {actionLabel, actionTone, basisText, countsLine, decideBody, driftLines, evidenceLine, familiesText, FILTER_TEXT, groupedRules, guardLines, hasPatch, jointLine, LADDER_TEXT,
  type ParamFilter, patchText, planBody, planLine, planWarnings, proposedText, registrySummary, statusText, sweepLine, sweepNotes, unregisteredLine, valueText,
} from "../utils/tuning";

interface Props {
  drawingId: string;
  canEdit: boolean;
}

const BTN = "rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[11.5px] disabled:opacity-50";
const INPUT = "mt-0.5 w-full rounded-[8px] border border-[var(--color-border)] bg-transparent px-2 py-1 text-[11.5px]";
const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";
const ERR = "text-[11.5px] text-[var(--color-danger,#b42318)]";

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function copyText(text: string, ok: () => void, fail: () => void) {
  const clip = typeof navigator !== "undefined" ? navigator.clipboard : undefined;
  if (!clip) { fail(); return; }
  clip.writeText(text).then(ok, fail);
}

function RegistryView({ reg }: { reg: TuningRegistry }) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<ParamFilter>("ALL");
  const drift = driftLines(reg);
  const unreg = unregisteredLine(reg);
  const groups = groupedRules(reg, filter);
  return (
    <section data-testid="tuning-registry">
      <p className="font-semibold">{t("boq.takeoff.tuning.registry", "The rules and their numbers")}</p>
      <p className={MUTED} data-testid="tuning-summary">{registrySummary(reg)}</p>
      {unreg ? <p className={MUTED} data-testid="tuning-unregistered">{unreg}</p> : null}
      {drift.length ? (
        <ul className="list-disc pl-4 text-[11.5px] text-[var(--color-danger,#b42318)]" data-testid="tuning-drift">{drift.map((x) => <li key={x}>{x}</li>)}</ul>
      ) : null}
      <label className="mt-1 flex items-center gap-1.5">
        {t("boq.takeoff.tuning.show", "Show")}
        <select value={filter} onChange={(e) => setFilter(e.target.value as ParamFilter)} className="rounded-[8px] border border-[var(--color-border)] bg-transparent px-1 py-0.5" data-testid="tuning-filter">
          {(Object.keys(FILTER_TEXT) as ParamFilter[]).map((f) => <option key={f} value={f}>{FILTER_TEXT[f]}</option>)}
        </select>
      </label>
      <div className="mt-1 space-y-2">
        {groups.map(({ rule, params }) => (
          <div key={rule.id} data-testid={`tuning-rule-${rule.id}`}>
            <p>
              <span className="font-medium">{rule.label}</span>
              <span className="ml-2"><Badge tone={rule.basis === "TUNED" ? "gold" : "slate"}>{basisText(rule.basis)}</Badge></span>
              <span className={`ml-2 ${MUTED}`}>{familiesText(rule.families)}</span>
            </p>
            {params.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11.5px]">
                  <thead>
                    <tr className="text-[var(--color-text-secondary)]">
                      <th className="pr-2">{t("boq.takeoff.tuning.name", "Number")}</th>
                      <th className="pr-2">{t("boq.takeoff.tuning.now", "Now")}</th>
                      <th className="pr-2">{t("boq.takeoff.tuning.hand", "By hand")}</th>
                      <th className="pr-2">{t("boq.takeoff.tuning.range", "Allowed")}</th>
                      <th>{t("boq.takeoff.tuning.can", "What a sweep can do")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {params.map((p) => (
                      <tr key={p.key} data-testid={`tuning-param-${p.key}`}>
                        <td className="pr-2 font-mono">{p.name}</td>
                        <td className="pr-2">{valueText(p.live, p.unit)}</td>
                        <td className="pr-2">{valueText(p.hand, p.unit)}</td>
                        <td className="pr-2">{`${valueText(p.lo, p.unit)} – ${valueText(p.hi, p.unit)}`}</td>
                        <td>{statusText(p)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className={MUTED}>{t("boq.takeoff.tuning.noNumbers", "No number of its own to sweep.")}</p>}
          </div>
        ))}
        {!groups.length ? <p className={MUTED}>{t("boq.takeoff.tuning.noMatch", "Nothing matches.")}</p> : null}
      </div>
    </section>
  );
}

function PlanBuilder({ reg, drawingId }: { reg: TuningRegistry; drawingId: string }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const plan = useTuningPlan(drawingId);
  const [rule, setRule] = useState("");
  const [ladder, setLadder] = useState<Ladder>("standard");
  const [copies, setCopies] = useState("");
  const [control, setControl] = useState("");
  const [unswept, setUnswept] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TuningPlan | null>(null);

  const onPlan = () => {
    const b = planBody({ rule, ladder, copies, controlSeconds: control, includeUnswept: unswept });
    if (!b.ok) { setError(b.error); return; }
    setError("");
    plan.mutate(b.body, { onSuccess: setResult, onError: (e) => setError(takeoffErrorMessage(e)) });
  };
  const onCopy = () => {
    if (!result) return;
    copyText(result.command, () => showToast({ tone: "success", title: t("boq.takeoff.tuning.copied", "Command copied.") }), () => showToast({ tone: "error", title: t("boq.takeoff.tuning.copyFail", "Could not copy. Select the command and copy it by hand.") }));
  };
  const warnings = result ? planWarnings(result) : [];
  return (
    <section data-testid="tuning-plan">
      <p className="font-semibold">{t("boq.takeoff.tuning.plan", "Plan a sweep")}</p>
      <p className={MUTED}>{t("boq.takeoff.tuning.planHint", "A sweep reads the sheets many times, so it runs from the command line on a copy of the code, never here. This shows what it would run and the command to start it.")}</p>
      <div className="mt-1 grid gap-2 sm:grid-cols-2">
        <label className="block">{t("boq.takeoff.tuning.rule", "Rule")}
          <select value={rule} onChange={(e) => setRule(e.target.value)} className={INPUT} data-testid="tuning-plan-rule">
            <option value="">{t("boq.takeoff.tuning.allRules", "Every tuned rule")}</option>
            {reg.rules.filter((r) => r.sweepable > 0).map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
          </select>
        </label>
        <label className="block">{t("boq.takeoff.tuning.ladder", "Values tried")}
          <select value={ladder} onChange={(e) => setLadder(e.target.value as Ladder)} className={INPUT} data-testid="tuning-plan-ladder">
            {(Object.keys(LADDER_TEXT) as Ladder[]).map((l) => <option key={l} value={l}>{LADDER_TEXT[l]}</option>)}
          </select>
        </label>
        <label className="block sm:col-span-2">{t("boq.takeoff.tuning.copies", "Copies of the drawing to include (their ids, optional)")}
          <textarea value={copies} onChange={(e) => setCopies(e.target.value)} rows={2} className={`${INPUT} font-mono`} data-testid="tuning-plan-copies" />
        </label>
        <label className="block">{t("boq.takeoff.tuning.control", "Seconds one full read takes (optional)")}
          <input value={control} onChange={(e) => setControl(e.target.value)} inputMode="decimal" className={INPUT} data-testid="tuning-plan-control" />
        </label>
        <label className="flex items-center gap-1.5 self-end"><input type="checkbox" checked={unswept} onChange={(e) => setUnswept(e.target.checked)} />{t("boq.takeoff.tuning.unswept", "Also sweep numbers a score does not change")}</label>
      </div>
      <div className="mt-1.5 flex items-center gap-2">
        <button type="button" className={BTN} disabled={plan.isPending} onClick={onPlan} data-testid="tuning-plan-go">{plan.isPending ? t("boq.takeoff.tuning.planning", "Working out…") : t("boq.takeoff.tuning.planGo", "Show the plan")}</button>
        {error ? <span className={ERR} data-testid="tuning-plan-error">{error}</span> : null}
      </div>
      {result ? (
        <div className="mt-2 space-y-1" data-testid="tuning-plan-result">
          <p className="font-medium" data-testid="tuning-plan-line">{planLine(result)}</p>
          <p className={MUTED}>{`${result.labels} labelled member${result.labels === 1 ? "" : "s"} on ${result.complete_sheets} complete sheet${result.complete_sheets === 1 ? "" : "s"}.`}</p>
          {warnings.length ? <ul className="list-disc pl-4 text-[11.5px] text-[var(--color-danger,#b42318)]" data-testid="tuning-plan-warnings">{warnings.map((w) => <li key={w}>{w}</li>)}</ul> : null}
          <pre className="overflow-x-auto rounded-[8px] border border-[var(--color-border)] p-2 font-mono text-[11px]" data-testid="tuning-plan-command">{result.command}</pre>
          <button type="button" className={BTN} onClick={onCopy} data-testid="tuning-plan-copy">{t("boq.takeoff.tuning.copy", "Copy the command")}</button>
        </div>
      ) : null}
    </section>
  );
}

function PatchView({ patch }: { patch: Patch }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  if (!hasPatch(patch)) return <p className={MUTED}>{t("boq.takeoff.tuning.noPatch", "Nothing to change in the code.")}</p>;
  const onCopy = (text: string) => copyText(text, () => showToast({ tone: "success", title: t("boq.takeoff.tuning.copied", "Copied.") }), () => showToast({ tone: "error", title: t("boq.takeoff.tuning.copyFail", "Could not copy. Select the text and copy it by hand.") }));
  return (
    <div className="space-y-1" data-testid="tuning-patch">
      <p className="font-semibold">{t("boq.takeoff.tuning.patch", "Changes to the code")}</p>
      <p className={MUTED}>{t("boq.takeoff.tuning.patchHint", "Apply them by hand, one at a time, then run the tests and a score. The reader version goes up with the first one.")}</p>
      <pre className="max-h-64 overflow-auto rounded-[8px] border border-[var(--color-border)] p-2 font-mono text-[11px]" data-testid="tuning-patch-text">{patchText(patch)}</pre>
      <div className="flex gap-2">
        <button type="button" className={BTN} onClick={() => onCopy(patchText(patch))} data-testid="tuning-patch-copy">{t("boq.takeoff.tuning.copyPatch", "Copy the changes")}</button>
        {patch.markdown ? <button type="button" className={BTN} onClick={() => onCopy(patch.markdown)} data-testid="tuning-report-copy">{t("boq.takeoff.tuning.copyReport", "Copy the report")}</button> : null}
      </div>
    </div>
  );
}

function DecisionsView({ d, unitOf }: { d: Decisions; unitOf: (key: string) => string }) {
  const { t } = useTranslation();
  const joint = jointLine(d);
  return (
    <div className="space-y-1" data-testid="tuning-decisions">
      <p className={MUTED}>{countsLine(d.counts)}</p>
      {joint ? <p className={MUTED} data-testid="tuning-joint">{joint}</p> : null}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[11.5px]">
          <thead>
            <tr className="text-[var(--color-text-secondary)]">
              <th className="pr-2">{t("boq.takeoff.tuning.name", "Number")}</th>
              <th className="pr-2">{t("boq.takeoff.tuning.now", "Now")}</th>
              <th className="pr-2">{t("boq.takeoff.tuning.proposed", "Proposed")}</th>
              <th className="pr-2">{t("boq.takeoff.tuning.decision", "Decision")}</th>
              <th>{t("boq.takeoff.tuning.evidence", "Evidence")}</th>
            </tr>
          </thead>
          <tbody>
            {d.decisions.map((x) => (
              <tr key={x.key} data-testid={`tuning-decision-${x.key}`} className="align-top">
                <td className="pr-2 font-mono">{x.key.replace(/^[A-Z]+\./, "")}</td>
                <td className="pr-2">{valueText(x.current, unitOf(x.key))}</td>
                <td className="pr-2">{proposedText(x, unitOf(x.key))}</td>
                <td className="pr-2"><Badge tone={actionTone(x.action)}>{actionLabel(x.action)}</Badge></td>
                <td>
                  {evidenceLine(x)}
                  {guardLines(x).map((g) => <div key={g} className={MUTED}>{g}</div>)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {d.skipped.length ? <p className={MUTED}>{`${d.skipped.length} not swept.`}</p> : null}
    </div>
  );
}

function SweepView({ sweepId, unitOf, canEdit }: { sweepId: string; unitOf: (key: string) => string; canEdit: boolean }) {
  const { t } = useTranslation();
  const detail = useTuningSweep(sweepId);
  const again = useDecideAgain(sweepId);
  const [minLabels, setMinLabels] = useState("");
  const [minGain, setMinGain] = useState("");
  const [error, setError] = useState("");
  const [fresh, setFresh] = useState<{ decisions: Decisions; patch: Patch } | null>(null);
  if (detail.isLoading) return <p className={MUTED}>{"…"}</p>;
  if (detail.isError || !detail.data) return <p className={ERR}>{t("boq.takeoff.tuning.sweepError", "Could not load this sweep.")}</p>;
  const decisions = fresh?.decisions ?? detail.data.decisions;
  const patch = fresh?.patch ?? detail.data.patch;
  const onAgain = () => {
    const b = decideBody(minLabels, minGain);
    if (!b.ok) { setError(b.error); return; }
    setError("");
    again.mutate(b.body, { onSuccess: (r) => setFresh({ decisions: r.decisions, patch: r.patch }), onError: (e) => setError(takeoffErrorMessage(e)) });
  };
  return (
    <div className="mt-2 space-y-2" data-testid="tuning-sweep-detail">
      <DecisionsView d={decisions} unitOf={unitOf} />
      <PatchView patch={patch} />
      {canEdit ? (
        <div className="space-y-1" data-testid="tuning-decide">
          <p className="font-semibold">{t("boq.takeoff.tuning.decideAgain", "Decide again with other limits")}</p>
          <p className={MUTED}>{`Now: ${decisions.policy.min_labels} labelled members, a gain of at least ${decisions.policy.min_gain}. Nothing is read again and nothing is saved.`}</p>
          <div className="flex flex-wrap items-end gap-2">
            <label className="block">{t("boq.takeoff.tuning.minLabels", "Labelled members needed")}
              <input value={minLabels} onChange={(e) => setMinLabels(e.target.value)} inputMode="numeric" className={INPUT} data-testid="tuning-min-labels" />
            </label>
            <label className="block">{t("boq.takeoff.tuning.minGain", "Smallest gain (0 to 1)")}
              <input value={minGain} onChange={(e) => setMinGain(e.target.value)} inputMode="decimal" className={INPUT} data-testid="tuning-min-gain" />
            </label>
            <button type="button" className={BTN} disabled={again.isPending} onClick={onAgain} data-testid="tuning-decide-go">{t("boq.takeoff.tuning.decideGo", "Decide again")}</button>
          </div>
          {error ? <p className={ERR} data-testid="tuning-decide-error">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function SweepRow({ s, current, open, onOpen, onDelete, canEdit, deleting }: { s: SweepItem; current: number; open: boolean; onOpen: () => void; onDelete: () => void; canEdit: boolean; deleting: boolean }) {
  const notes = sweepNotes(s, current);
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`tuning-sweep-${s.id}`}>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className="font-medium underline" onClick={onOpen} aria-expanded={open}>{when(s.created_at)}</button>
        {s.status === "PARTIAL" ? <Badge tone="gold">Partial</Badge> : null}
        {s.stale ? <Badge tone="red">Out of date</Badge> : null}
        <span className={MUTED}>{sweepLine(s)}</span>
        {canEdit ? <button type="button" className={`${BTN} ml-auto`} disabled={deleting} onClick={onDelete} data-testid={`tuning-delete-${s.id}`}>Delete</button> : null}
      </div>
      {notes.map((n) => <p key={n} className={ERR}>{n}</p>)}
    </li>
  );
}

export function TuningPanel({ drawingId, canEdit }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState<string | null>(null);
  const registry = useTuningRegistry(open);
  const sweeps = useTuningSweeps(drawingId, open);
  const remove = useDeleteSweep(drawingId);
  const reg = registry.data;
  const unitOf = (key: string) => reg?.params.find((p) => p.key === key)?.unit ?? "";
  const list = sweeps.data?.sweeps ?? [];
  const current = sweeps.data?.current_extract_version ?? reg?.extract_version ?? 0;
  const onDelete = (id: string) => {
    if (!window.confirm(t("boq.takeoff.tuning.confirmDelete", "Delete this sweep? The numbers in the code are not touched."))) return;
    remove.mutate(id, { onSuccess: () => { if (shown === id) setShown(null); }, onError: (e) => showToast({ tone: "error", title: takeoffErrorMessage(e) }) });
  };
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="tuning-panel" onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer">
        <span className="font-semibold">{t("boq.takeoff.tuning.title", "Tuned reader rules")}</span>
        {reg ? <span className={`ml-2 ${MUTED}`}>{`Reader version ${reg.extract_version}`}</span> : null}
        {reg && reg.ledger.drift.length ? <span className="ml-2"><Badge tone="red">{`${reg.ledger.drift.length} to check`}</Badge></span> : null}
      </summary>
      <div className="mt-2 space-y-3">
        {registry.isLoading ? <p className={MUTED}>{"…"}</p> : null}
        {registry.isError ? <p className={ERR}>{t("boq.takeoff.tuning.loadError", "Could not load the rules.")}</p> : null}
        {reg ? <RegistryView reg={reg} /> : null}
        {reg ? <PlanBuilder reg={reg} drawingId={drawingId} /> : null}
        <section data-testid="tuning-sweeps">
          <p className="font-semibold">{t("boq.takeoff.tuning.sweeps", "Sweeps of this drawing")}</p>
          {sweeps.isError ? <p className={ERR}>{t("boq.takeoff.tuning.sweepsError", "Could not load the sweeps.")}</p> : null}
          {!sweeps.isLoading && !list.length ? <p className={MUTED}>{t("boq.takeoff.tuning.noSweeps", "No sweep yet. Plan one above and run the command.")}</p> : null}
          {list.length ? (
            <ul className="mt-1 space-y-1">
              {list.map((s) => (
                <SweepRow key={s.id} s={s} current={current} open={shown === s.id} canEdit={canEdit} deleting={remove.isPending} onOpen={() => setShown((x) => (x === s.id ? null : s.id))} onDelete={() => onDelete(s.id)} />
              ))}
            </ul>
          ) : null}
          {shown ? <SweepView key={shown} sweepId={shown} unitOf={unitOf} canEdit={canEdit} /> : null}
        </section>
      </div>
    </details>
  );
}
