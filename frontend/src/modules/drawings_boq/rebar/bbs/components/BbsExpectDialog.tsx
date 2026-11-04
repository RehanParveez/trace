import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { EXPECT_PAGE_SIZE } from "../api/bbsExpect.api";
import { useBbsExpectItems, useBbsExpectRun, useRunBbsExpect, useSaveDecision } from "../hooks/useBbsExpect";
import { useBbsDecisions } from "../hooks/useBbsMatch";
import { HEIGHT_FLOORS, STOCK_ASSUMED_FT, completeLabel, flagText, heightsPayload, inputValueText, kgText, numberOrNull, parseMemberInputs, shareRows, stateTone } from "../utils/bbsExpect";
import type { BbsDocumentSummary } from "../types/bbsAudit.types";
import type { ExpectFilters, Expectation, MemberClass } from "../types/bbsExpect.types";

interface BbsExpectDialogProps {
  projectId: string;
  document: BbsDocumentSummary;
  canEdit: boolean;
  onClose: () => void;
}

const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const field = "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px]";
const CLASSES: MemberClass[] = ["COLUMN", "BEAM", "FOOTING", "PLINTH", "SLAB", "LINTEL", "TANK"];
const TRI = [["", "no decision (assumed)"], ["true", "yes"], ["false", "no"]] as const;

export function BbsExpectDialog({ projectId, document, canEdit, onClose }: BbsExpectDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [filters, setFilters] = useState<ExpectFilters>({ member_class: "", complete: "", page: 1 });
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [heights, setHeights] = useState<Record<string, string>>({});
  const [memberText, setMemberText] = useState("");
  const run = useBbsExpectRun(document.id);
  const items = useBbsExpectItems(document.id, filters);
  const start = useRunBbsExpect(document.id);
  const decisions = useBbsDecisions(projectId);
  const save = useSaveDecision(projectId);
  const stored = decisions.data?.decisions;
  const data = items.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / EXPECT_PAGE_SIZE)) : 1;

  useEffect(() => {
    if (!stored) return;
    const s = (k: string) => (stored[k] === undefined || stored[k] === null ? "" : String(stored[k]));
    const hook = (stored.hook_lengths ?? {}) as Record<string, number>;
    setDraft({ stock_length_ft: s("stock_length_ft"), column_l0: s("column_l0"), tie_zones: s("tie_zones"), strip_junction: s("strip_junction"), link_cut_basis: s("link_cut_basis"), bar_count_plus_one: s("bar_count_plus_one"),
      round_whole_bars: s("round_whole_bars"), curtail_extras: s("curtail_extras"), hook_tie_d: hook.tie_d === undefined ? "" : String(hook.tie_d), hook_bar_d: hook.bar_d === undefined ? "" : String(hook.bar_d) });
    const h = (stored.floor_heights_ft ?? {}) as Record<string, number>;
    setHeights(Object.fromEntries(HEIGHT_FLOORS.map((f) => [f, h[f] === undefined ? "" : String(h[f])])));
    setMemberText(stored.member_inputs ? JSON.stringify(stored.member_inputs, null, 2) : "");
  }, [stored]);

  function saveDecision(key: string, value: unknown) {
    setError(null);
    save.mutate({ key, value }, {
      onSuccess: () => showToast({ tone: "success", title: t("bbs.expect.saved", "Decision saved. Work the quantities out again to use it.") }),
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.expect.saveError", "Couldn't save this decision."))),
    });
  }

  function saveNumber(key: string) {
    const n = numberOrNull(draft[key] ?? "");
    if (n === "bad") { setError(t("bbs.expect.number", "Enter a number.")); return; }
    saveDecision(key, n);
  }

  function saveChoice(key: string, bool: boolean) {
    const v = draft[key] ?? "";
    saveDecision(key, v === "" ? null : bool ? v === "true" : v);
  }

  function saveHooks() {
    const a = numberOrNull(draft.hook_tie_d ?? ""), b = numberOrNull(draft.hook_bar_d ?? "");
    if (a === "bad" || b === "bad") { setError(t("bbs.expect.number", "Enter a number.")); return; }
    const value: Record<string, number> = {};
    if (a !== null) value.tie_d = a;
    if (b !== null) value.bar_d = b;
    saveDecision("hook_lengths", Object.keys(value).length ? value : null);
  }

  function saveHeights() {
    const p = heightsPayload(heights);
    if (p === "bad") { setError(t("bbs.expect.number", "Enter a number.")); return; }
    saveDecision("floor_heights_ft", Object.keys(p).length ? p : null);
  }

  function saveMembers() {
    const p = parseMemberInputs(memberText);
    if (!p.ok) { setError(t("bbs.expect.json", "The member inputs are not a table of CLASS:MARK to inputs.")); return; }
    saveDecision("member_inputs", Object.keys(p.value).length ? p.value : null);
  }

  function startRun() {
    setError(null);
    start.mutate(undefined, {
      onSuccess: () => { setFilters({ ...filters, page: 1 }); showToast({ tone: "success", title: t("bbs.expect.done", "Expected quantities worked out") }); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.expect.error", "Couldn't work out the expected quantities."))),
    });
  }

  const numberRow = (key: string, label: string, hint: string) => (
    <label className="flex flex-wrap items-center gap-2 text-[12px]" key={key}>
      <span className="min-w-[220px]">{label}</span>
      <input className={`${field} w-24`} value={draft[key] ?? ""} disabled={!canEdit} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />
      {canEdit ? <Button variant="ghost" size="sm" disabled={save.isPending} onClick={() => saveNumber(key)}>{t("bbs.expect.save", "Save")}</Button> : null}
      <span className="text-[var(--color-text-muted)]">{hint}</span>
    </label>
  );

  const choiceRow = (key: string, label: string, options: ReadonlyArray<readonly [string, string]>, bool: boolean) => (
    <label className="flex flex-wrap items-center gap-2 text-[12px]" key={key}>
      <span className="min-w-[220px]">{label}</span>
      <select className={field} value={draft[key] ?? ""} disabled={!canEdit} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}>
        {options.map(([v, text]) => <option key={v} value={v}>{text}</option>)}
      </select>
      {canEdit ? <Button variant="ghost" size="sm" disabled={save.isPending} onClick={() => saveChoice(key, bool)}>{t("bbs.expect.save", "Save")}</Button> : null}
    </label>
  );

  function lineTable(e: Expectation) {
    return (
      <table className="w-full text-left text-[12px]">
        <thead><tr><th className={th}>{t("bbs.expect.line", "Bars")}</th><th className={th}>#</th><th className={`${th} text-right`}>{t("bbs.expect.count", "Count")}</th>
          <th className={`${th} text-right`}>{t("bbs.expect.cut", "Cut ft")}</th><th className={`${th} text-right`}>{t("bbs.expect.laps", "Laps")}</th>
          <th className={`${th} text-right`}>{t("bbs.expect.totalFt", "Total ft")}</th><th className={`${th} text-right`}>kg</th></tr></thead>
        <tbody>{e.lines.map((l, i) => (
          <tr key={`${l.role}-${i}`} className="border-t border-[var(--color-border)]">
            <td className="px-3 py-1.5">{l.role}{l.note ? <span className="text-[var(--color-text-muted)]"> · {l.note}</span> : null}</td><td className="px-3 py-1.5">{l.dia ?? "—"}</td>
            <td className="px-3 py-1.5 text-right font-mono">{l.count ?? "—"}</td><td className="px-3 py-1.5 text-right font-mono">{l.cut_ft ?? "—"}</td>
            <td className="px-3 py-1.5 text-right font-mono">{l.laps}</td><td className="px-3 py-1.5 text-right font-mono">{l.total_ft ?? "—"}</td><td className="px-3 py-1.5 text-right font-mono">{kgText(l.kg)}</td>
          </tr>))}</tbody>
      </table>
    );
  }

  return (
    <Modal title={t("bbs.expect.title", "Expected quantities · version {{v}}", { v: document.version })} description={document.file_name ?? undefined} onClose={onClose} wide>
      <div className="space-y-4" data-testid="bbs-expect-dialog">
        <div className="flex flex-wrap items-center gap-2">
          {run.data ? <Badge tone={run.data.complete_count === run.data.member_count ? "green" : "gold"}>{t("bbs.expect.complete", "{{n}} members complete", { n: completeLabel(run.data) })}</Badge> : null}
          {shareRows(run.data).map((r) => <Badge key={r.state} tone={stateTone(r.state)}>{r.state.toLowerCase()} {r.percent} ({r.count})</Badge>)}
          {canEdit ? (
            <div className="ml-auto"><Button variant="secondary" size="sm" disabled={start.isPending} onClick={startRun}>
              {start.isPending ? t("bbs.expect.running", "Working out…") : run.data ? t("bbs.expect.rerun", "Work out again") : t("bbs.expect.run", "Work out expected quantities")}
            </Button></div>
          ) : null}
        </div>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <p className="text-[12px] text-[var(--color-text-secondary)]">{t("bbs.expect.note", "A quantity is shown only when every input it needs is known. Missing inputs are listed on each member and are never guessed; a defaulted input is marked as assumed.")}</p>

        <details className="rounded-[8px] border border-[var(--color-border)] p-3">
          <summary className="cursor-pointer text-[12.5px] font-semibold">{t("bbs.expect.decisions", "Decisions")}</summary>
          <div className="mt-2 space-y-2">
            {numberRow("stock_length_ft", t("bbs.expect.stock", "Stock bar length (ft)"), t("bbs.expect.stockHint", "Empty: {{n}} ft is assumed and laps are marked unsure.", { n: STOCK_ASSUMED_FT }))}
            {choiceRow("tie_zones", t("bbs.expect.zones", "Ties and stirrups"), [["", "no decision (zones)"], ["ZONES", "by zones"], ["AVERAGE", "one average spacing"]], false)}
            {choiceRow("bar_count_plus_one", t("bbs.expect.plusOne", "Add one to bar counts"), TRI, true)}
            {choiceRow("round_whole_bars", t("bbs.expect.whole", "Round bars up to whole bars"), TRI, true)}
            {choiceRow("curtail_extras", t("bbs.expect.curtail", "Curtail extra bars"), TRI, true)}
            {choiceRow("strip_junction", t("bbs.expect.junction", "Strip junctions"), [["", "no decision (counted once)"], ["ONCE", "counted once"], ["EACH_STRIP", "in each strip"]], false)}
            {choiceRow("link_cut_basis", t("bbs.expect.linkBasis", "Ring and stirrup cut length"), [["", "no decision (cover deducted, hooks added)"], ["NET", "cover deducted, hooks added"], ["PERIMETER", "outside perimeter of the member"]], false)}
            {numberRow("column_l0", t("bbs.expect.l0", "Column end-zone length (in)"), t("bbs.expect.l0Hint", "Empty: the largest of the column side, H/6 and 18 in."))}
            <div className="flex flex-wrap items-center gap-2 text-[12px]">
              <span className="min-w-[220px]">{t("bbs.expect.hooks", "Hook lengths (× bar diameter)")}</span>
              <input className={`${field} w-20`} placeholder="tie" value={draft.hook_tie_d ?? ""} disabled={!canEdit} onChange={(e) => setDraft({ ...draft, hook_tie_d: e.target.value })} />
              <input className={`${field} w-20`} placeholder="bar" value={draft.hook_bar_d ?? ""} disabled={!canEdit} onChange={(e) => setDraft({ ...draft, hook_bar_d: e.target.value })} />
              {canEdit ? <Button variant="ghost" size="sm" disabled={save.isPending} onClick={saveHooks}>{t("bbs.expect.save", "Save")}</Button> : null}
            </div>
            <div className="space-y-1">
              <div className="text-[12px] font-semibold">{t("bbs.expect.heights", "Floor heights (ft)")}</div>
              <div className="flex flex-wrap gap-2">
                {HEIGHT_FLOORS.map((f) => (
                  <label key={f} className="text-[11px]">{f}
                    <input className={`${field} block w-20`} value={heights[f] ?? ""} disabled={!canEdit} onChange={(e) => setHeights({ ...heights, [f]: e.target.value })} />
                  </label>
                ))}
                {canEdit ? <Button variant="ghost" size="sm" disabled={save.isPending} onClick={saveHeights}>{t("bbs.expect.save", "Save")}</Button> : null}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[12px] font-semibold">{t("bbs.expect.members", "Member inputs the drawings do not give (spans, strip lengths, bar callouts)")}</div>
              <textarea className={`${field} h-32 w-full font-mono`} value={memberText} disabled={!canEdit} onChange={(e) => setMemberText(e.target.value)}
                placeholder={'{"BEAM:B1": {"span_ft": 14}, "FOOTING:F1": {"strip_length_ft": 396, "width_in": 48}}'} />
              {canEdit ? <Button variant="ghost" size="sm" disabled={save.isPending} onClick={saveMembers}>{t("bbs.expect.save", "Save")}</Button> : null}
            </div>
          </div>
        </details>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant={filters.member_class === "" ? "primary" : "ghost"} size="sm" onClick={() => setFilters({ ...filters, member_class: "", page: 1 })}>{t("bbs.expect.all", "All")}</Button>
          {CLASSES.map((c) => <Button key={c} variant={filters.member_class === c ? "primary" : "ghost"} size="sm" onClick={() => setFilters({ ...filters, member_class: c, page: 1 })}>{c} {data?.counts_by_class[c] ?? ""}</Button>)}
          <select className={field} value={filters.complete} onChange={(e) => setFilters({ ...filters, complete: e.target.value as ExpectFilters["complete"], page: 1 })}>
            <option value="">{t("bbs.expect.anyState", "Complete or not")}</option><option value="yes">{t("bbs.expect.onlyComplete", "Complete")}</option><option value="no">{t("bbs.expect.onlyOpen", "Not complete")}</option>
          </select>
        </div>

        {items.isLoading ? <LoadingState label={t("bbs.expect.loading", "Loading…")} /> : items.isError ? (
          <ErrorState title={t("bbs.expect.loadError", "Couldn't load the expected quantities")} onRetry={() => void items.refetch()} />
        ) : !data || data.run_id === null ? (
          <EmptyState title={t("bbs.expect.none", "Not worked out yet")} description={t("bbs.expect.noneDesc", "Run it once the structural drawings have been prepared.")} />
        ) : data.items.length === 0 ? <EmptyState title={t("bbs.expect.noItems", "No members here")} description={t("bbs.expect.noItemsDesc", "Change the filters above to see other members.")} /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead><tr><th className={th}>{t("bbs.expect.member", "Member")}</th><th className={th}>{t("bbs.expect.floor", "Floor")}</th><th className={th}>{t("bbs.expect.status", "Status")}</th>
                <th className={`${th} text-right`}>{t("bbs.expect.onPlan", "On plan")}</th><th className={`${th} text-right`}>kg</th><th className={th}>{t("bbs.expect.needs", "Needs")}</th></tr></thead>
              <tbody>
                {data.items.map((e) => (
                  <Fragment key={e.id}>
                    <tr className="cursor-pointer border-t border-[var(--color-border)]" onClick={() => setOpen(open === e.id ? null : e.id)}>
                      <td className="px-3 py-2 text-[12.5px] font-semibold">{e.member_class} {e.mark}{e.decision_only ? <span className="text-[var(--color-text-muted)]"> · {t("bbs.expect.fromDecision", "from a decision")}</span> : null}</td>
                      <td className="px-3 py-2 text-[12px]">{e.floor ? e.floor.toLowerCase() : "—"}</td>
                      <td className="px-3 py-2"><Badge tone={e.complete ? "green" : "gold"}>{e.complete ? t("bbs.expect.isComplete", "complete") : t("bbs.expect.isOpen", "incomplete")}</Badge></td>
                      <td className="px-3 py-2 text-right font-mono text-[12px]">{e.plan_count ?? "—"}</td>
                      <td className="px-3 py-2 text-right font-mono text-[12px]">{kgText(e.kg)}</td>
                      <td className="px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">{e.blocked.slice(0, 3).join(", ")}{e.blocked.length > 3 ? " …" : ""}</td>
                    </tr>
                    {open === e.id ? (
                      <tr><td colSpan={6} className="space-y-3 bg-[var(--color-surface-muted)] px-3 py-3">
                        {e.lines.length > 0 ? lineTable(e) : null}
                        {e.notes.map((n) => <div key={n} className="text-[12px] text-[var(--color-text-secondary)]">{n}</div>)}
                        <div className="grid gap-1 text-[12px] md:grid-cols-2">
                          {e.inputs.map((i) => (
                            <div key={i.name} className="flex flex-wrap items-center gap-2">
                              <Badge tone={stateTone(i.state)}>{i.state.toLowerCase()}</Badge>
                              <span className="font-mono">{i.name} = {inputValueText(i)}</span>
                              <span className="text-[var(--color-text-muted)]">{i.source}{i.flag ? ` · ${flagText(i.flag)}` : ""}</span>
                            </div>
                          ))}
                        </div>
                      </td></tr>
                    ) : null}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > EXPECT_PAGE_SIZE ? (
          <div className="flex items-center justify-end gap-2 text-[12px]">
            <Button variant="ghost" size="sm" disabled={filters.page <= 1} onClick={() => setFilters({ ...filters, page: filters.page - 1 })}>‹</Button>
            <span>{filters.page} / {pages}</span>
            <Button variant="ghost" size="sm" disabled={filters.page >= pages} onClick={() => setFilters({ ...filters, page: filters.page + 1 })}>›</Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
