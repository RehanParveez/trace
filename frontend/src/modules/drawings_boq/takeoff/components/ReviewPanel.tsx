import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import { useCombineFloorSources, useMemberLinks, useResolveConflicts, useReviewFloors, useSteelRollup, useValueConflicts } from "../hooks/useReview";
import type { CombineResult, ConflictsResult, FactDecision, LinksResult, SteelRollup, ValueConflict } from "../types/review.types";
import type { FloorSources } from "../types/takeoff.types";
import {BY_LABEL, KIND_LABEL, LINK_GROUP_LABEL, LINK_REASON, LINK_STATUS_LABEL, POLICY_KINDS, policyOptionsFor, STEEL_FIELDS, STEEL_STATUS_LABEL, canChoose, choiceOf, conflictsByKind, conventionsFromInputs,
   TRUST_LABEL, factSourcesText, deltaText, kgText, linkTone, mmText, needsText, quantityText, rangeText, sourcesText, steelTone,
} from "../utils/review";

const MAX_OPEN_LINKS = 12;
const BOX = "space-y-2 rounded-[10px] border border-[var(--color-border)] p-3";
const HEAD = "flex flex-wrap items-center gap-2";
const TITLE = "text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const MUTED = "text-[11.5px] text-[var(--color-text-muted)]";

export function FloorsBlock({ floors, canEdit, busy, onCombine, last }: { floors: FloorSources | undefined; canEdit: boolean; busy: boolean; onCombine: () => void; last?: CombineResult }) {
  const { t } = useTranslation();
  const twoSheets = (floors?.floors ?? []).filter((f) => f.state === "DOUBLE" || f.state === "COMBINED");
  if (twoSheets.length === 0 && !(last?.blocked?.length)) return null;
  const open = twoSheets.filter((f) => f.state === "DOUBLE").length;
  return (
    <section className={BOX} data-testid="review-floors">
      <div className={HEAD}>
        <h3 className={TITLE}>{t("takeoff.review.floors.title", "Floors drawn on two sheets")}</h3>
        {open > 0 ? <Badge tone="gold">{t("takeoff.review.floors.open", { defaultValue: "{{n}} not combined", n: open })}</Badge> : <Badge tone="green">{t("takeoff.review.floors.done", "combined")}</Badge>}
      </div>
      <p>{t("takeoff.review.floors.help", "A floor drawn on its own sheet and again among the plans is laid over itself by its marks and positions. What both sheets show is counted once; what only one of them shows is kept.")}</p>
      <ul className="space-y-1">
        {twoSheets.map((f) => {
          const added = f.sources.reduce((a, s) => a + (s.added ?? 0), 0);
          const merged = f.sources.reduce((a, s) => a + (s.combined ?? 0), 0);
          const wall = f.sources.reduce((a, s) => a + (s.added_wall_m ?? 0), 0);
          return (
            <li key={f.floor} data-testid={`review-floor-${f.floor}`} data-state={f.state}>
              <span className="font-semibold text-[var(--color-text-primary)]">{f.floor}</span>{" "}
              {f.state === "COMBINED"
                ? t("takeoff.review.floors.combined", { defaultValue: "{{m}} repeated items counted once. {{a}} items only the second sheet shows wait for your approval{{w}}.", m: merged, a: added, w: wall > 0 ? t("takeoff.review.floors.wall", { defaultValue: " ({{m}} m of them wall)", m: wall.toFixed(1) }) : "" })
                : t("takeoff.review.floors.notYet", "both sheets are still counted. Combine them, or choose one sheet on the Measure page.")}
            </li>
          );
        })}
      </ul>
      {last?.blocked?.length ? (
        <ul className="list-disc pl-5 text-[var(--color-warning)]" data-testid="review-floors-blocked">
          {last.blocked.map((b) => <li key={`${b.floor}|${b.code}`}>{b.floor}: {b.message}</li>)}
        </ul>
      ) : null}
      {canEdit && twoSheets.length > 0 ? (
        <Button size="sm" variant={open > 0 ? "primary" : "secondary"} disabled={busy} onClick={onCombine} data-testid="review-combine">
          {busy ? t("takeoff.review.floors.working", "Combining…") : open > 0 ? t("takeoff.review.floors.combine", "Combine the two sheets of each floor") : t("takeoff.review.floors.again", "Combine again")}
        </Button>
      ) : null}
    </section>
  );
}

interface ConflictsProps {
  data: ConflictsResult | undefined;
  loading: boolean;
  error: boolean;
  policy: Record<string, string>;
  onPolicy: (kind: string, value: string) => void;
  canEdit: boolean;
  busy: boolean;
  onApplyPolicy: () => void;
  onChoose: (conflictId: string, value: number) => void;
  onChooseDecision?: (decisionId: string, value: string) => void;
  skipped?:Array<{ id: string; message: string }>;
}

function DecisionRow({ d, p }: { d: FactDecision; p: ConflictsProps }) {
  const { t } = useTranslation();
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`decision-fact-${d.id}`} data-open={d.open}>
      <p className="font-semibold text-[var(--color-text-primary)]">{d.question}</p>
      <p className={MUTED}>{t("takeoff.review.decision.rows", { defaultValue: "Settles {{n}} rows: {{facts}}", n: d.rows, facts: d.facts.slice(0, 4).map((k) => k.split(":").slice(1).join(":") || k).join(", ") + (d.facts.length > 4 ? ` +${d.facts.length - 4}` : "") })}</p>
      <ul className="mt-1 space-y-1">
        {d.options.map((o) => (
          <li key={o.value} className="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid={`decision-fact-${d.id}-${o.value}`} data-in-force={d.chosen === o.value}>
            <span className="font-semibold text-[var(--color-text-primary)]">{o.label ?? o.value}</span>
            {o.trust ? <Badge tone={o.default ? "green" : "slate"}>{TRUST_LABEL[o.trust] ?? o.trust}{o.default ? " · " + t("takeoff.review.decision.default", "more trusted") : ""}</Badge> : null}
            {o.quantity != null ? <span>{o.quantity.toLocaleString("en-US", { maximumFractionDigits: 2 })} {o.unit ?? ""}</span> : null}
            <span className={MUTED}>{factSourcesText(o.sources)}</span>
            {p.canEdit && p.onChooseDecision && d.chosen !== o.value ? (
              <Button size="sm" variant="ghost" disabled={p.busy} onClick={() => p.onChooseDecision?.(d.id, o.value)} data-testid={`decision-fact-use-${d.id}-${o.value}`}>
                {t("takeoff.review.decision.use", "Use for all rows")}
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
      {d.open && d.default == null ? <p className={MUTED}>{t("takeoff.review.decision.tied", "The sources are equally trusted, so this is left to you.")}</p> : null}
    </li>
  );
}

export function ConflictsBlock(p: ConflictsProps) {
  const { t } = useTranslation();
  const list = p.data?.conflicts ?? [];
  const groups = conflictsByKind(list);
  const undecided = p.data?.undecided ?? 0;
  return (
    <section className={BOX} data-testid="review-conflicts">
      <div className={HEAD}>
        <h3 className={TITLE}>{t("takeoff.review.conflicts.title", "Values the drawing prints two ways")}</h3>
        {list.length > 0 ? (undecided > 0 ? <Badge tone="gold">{t("takeoff.review.conflicts.undecided", { defaultValue: "{{n}} to settle", n: undecided })}</Badge> : <Badge tone="green">{t("takeoff.review.conflicts.settled", "settled")}</Badge>) : null}
      </div>
      {p.loading && !p.data ? <p data-testid="review-conflicts-loading">{t("takeoff.review.loading", "Checking…")}</p> : null}
      {p.error && !p.data ? <p className="text-[var(--color-danger)]">{t("takeoff.review.conflicts.failed", "Could not list the values just now.")}</p> : null}
      {p.data && list.length === 0 ? <p data-testid="review-conflicts-none">{t("takeoff.review.conflicts.none", "No value is printed two ways on this drawing.")}</p> : null}
      {list.length > 0 ? (
        <>
          <p>{t("takeoff.review.conflicts.help", "Where the architectural and the structural sheet disagree, both quantities are shown. The policy decides which one is used; a value you choose beats the policy. Nothing changes until you press a button.")}</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {POLICY_KINDS.filter((k) => (p.data?.by_kind?.[k] ?? 0) > 0).map((k) => (
              <label key={k} className="block">
                <span className="text-[11px] font-semibold text-[var(--color-text-primary)]">{t(`takeoff.review.kind.${k}`, KIND_LABEL[k])}</span>
                <select value={p.policy[k] ?? p.data?.policy?.[k] ?? "AS_READ"} onChange={(e) => p.onPolicy(k, e.target.value)} disabled={p.busy} data-testid={`review-policy-${k}`}
                  className="mt-1 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-[12px]">
                  {policyOptionsFor(k).map((o) => <option key={o.key} value={o.key}>{t(`takeoff.review.policy.${o.key}`, o.label)}</option>)}
                </select>
              </label>
            ))}
          </div>
          {p.canEdit ? (
            <Button size="sm" variant="secondary" disabled={p.busy || undecided === 0} onClick={p.onApplyPolicy} data-testid="review-apply-policy">
              {t("takeoff.review.conflicts.apply", "Use the policy for every open item")}
            </Button>
          ) : null}
          {(p.data?.decisions ?? []).length > 0 ? (
            <div className="space-y-2" data-testid="review-decisions">
              <p className="font-semibold text-[var(--color-text-primary)]">{t("takeoff.review.decision.title", "Decisions")} <span className="font-normal text-[var(--color-text-muted)]">· {(p.data?.decisions ?? []).length}</span></p>
              <ul className="space-y-2">{(p.data?.decisions ?? []).map((d) => <DecisionRow key={d.id} d={d} p={p} />)}</ul>
            </div>
          ) : null}
          {groups.map((g) => (
            <div key={g.kind} className="space-y-2" data-testid={`review-kind-${g.kind}`}>
              <p className="font-semibold text-[var(--color-text-primary)]">{t(`takeoff.review.kind.${g.kind}`, KIND_LABEL[g.kind] ?? g.kind)} <span className="font-normal text-[var(--color-text-muted)]">· {g.items.length}</span></p>
              <ul className="space-y-2">
                {g.items.map((c) => <ConflictRow key={c.id} c={c} p={p} />)}
              </ul>
            </div>
          ))}
          {p.skipped?.length ? (
            <ul className="list-disc pl-5 text-[var(--color-warning)]" data-testid="review-conflicts-skipped">
              {Array.from(new Set(p.skipped.map((s) => s.message))).map((m) => <li key={m}>{m}</li>)}
            </ul>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function ConflictRow({ c, p }: { c: ValueConflict; p: ConflictsProps }) {
  const { t } = useTranslation();
  const editable = p.canEdit && canChoose(c);
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`conflict-${c.id}`} data-by={c.governing_by ?? ""}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-[var(--color-text-primary)]">{c.subject}</span>
        {c.page_no ? <span className={MUTED}>{t("takeoff.review.page", { defaultValue: "page {{n}}", n: c.page_no })}</span> : null}
        {c.decision !== "NEW" ? <Badge tone="slate">{t("takeoff.review.decided", "already approved")}</Badge> : null}
        {c.governing_by ? <Badge tone={c.governing_by === "CHOSEN" ? "green" : "blue"}>{t(`takeoff.review.by.${c.governing_by}`, BY_LABEL[c.governing_by] ?? c.governing_by)}</Badge> : null}
      </div>
      <ul className="mt-1 space-y-1">
        {c.values.map((v, i) => {
          const q = quantityText(c, v);
          const d = deltaText(c, v);
          const used = c.governing_index === i;
          return (
            <li key={`${c.id}-${i}`} className="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid={`conflict-${c.id}-${i}`} data-in-force={used}>
              <span className={used ? "font-semibold text-[var(--color-text-primary)]" : ""}>{v.label}{v.value_mm !== null && !v.label.includes("mm") ? ` (${mmText(v.value_mm)})` : ""}</span>
              {v.steel_text ? <span className={MUTED}>{v.steel_text}</span> : null}
              <span className={MUTED}>{sourcesText(v)}</span>
              <span className="ml-auto flex items-center gap-2">
                {q ? <span className="font-semibold text-[var(--color-text-primary)]" data-testid={`conflict-${c.id}-${i}-qty`}>{q}</span> : null}
                {d ? <span className={MUTED}>{d}</span> : null}
                {used ? <Badge tone="green">{t("takeoff.review.inForce", "in force")}</Badge> : null}
                {editable && !(used && c.governing_by === "CHOSEN") && choiceOf(v) !== null ? (
                  <Button size="sm" variant="ghost" disabled={p.busy} onClick={() => p.onChoose(c.id, choiceOf(v) as number)} data-testid={`conflict-use-${c.id}-${i}`}>
                    {t("takeoff.review.use", "Use this")}
                  </Button>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
    </li>
  );
}

export function LinksBlock({ data, loading, error }: { data: LinksResult | undefined; loading: boolean; error: boolean }) {
  const { t } = useTranslation();
  if (!data && !loading && !error) return null;
  const open = (data?.items ?? []).filter((i) => i.status !== "LINKED");
  return (
    <section className={BOX} data-testid="review-links">
      <div className={HEAD}>
        <h3 className={TITLE}>{t("takeoff.review.links.title", "Details found for each member")}</h3>
        {data ? (data.open > 0 ? <Badge tone="gold">{t("takeoff.review.links.open", { defaultValue: "{{n}} open", n: data.open })}</Badge> : <Badge tone="green">{t("takeoff.review.links.allLinked", "all linked")}</Badge>) : null}
      </div>
      {loading && !data ? <p>{t("takeoff.review.loading", "Checking…")}</p> : null}
      {error && !data ? <p className="text-[var(--color-danger)]">{t("takeoff.review.links.failed", "Could not check the members just now.")}</p> : null}
      {data && data.groups.length === 0 ? <p>{t("takeoff.review.links.none", "No beam, footing, neck column or tank was found.")}</p> : null}
      {data && data.groups.length > 0 ? (
        <>
          <p>{t("takeoff.review.links.help", "The section, footing, column or tank detail that is printed on the drawing, and whether it was put on the member it belongs to.")}</p>
          <ul className="space-y-0.5">
            {data.groups.map((g) => (
              <li key={g.group} className="flex flex-wrap items-center gap-2" data-testid={`links-group-${g.group}`}>
                <span className="font-semibold text-[var(--color-text-primary)]">{t(`takeoff.review.group.${g.group}`, LINK_GROUP_LABEL[g.group] ?? g.group)}</span>
                <span>{t("takeoff.review.links.line", { defaultValue: "{{linked}} of {{total}} linked", linked: g.linked, total: g.total })}</span>
                {g.total - g.linked > 0 ? <span className={MUTED}>· {t("takeoff.review.links.openOf", { defaultValue: "{{n}} open", n: g.total - g.linked })}</span> : null}
              </li>
            ))}
          </ul>
          {open.length > 0 ? (
            <ul className="space-y-1 border-t border-[var(--color-border)] pt-2" data-testid="links-open">
              {open.slice(0, MAX_OPEN_LINKS).map((i) => (
                <li key={i.id} data-testid={`link-${i.id}`} data-status={i.status}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={linkTone(i.status)}>{t(`takeoff.review.status.${i.status}`, LINK_STATUS_LABEL[i.status])}</Badge>
                    <span className="font-semibold text-[var(--color-text-primary)]">{i.tag || i.label || t(`takeoff.review.group.${i.group}`, LINK_GROUP_LABEL[i.group] ?? i.group)}</span>
                    {i.floor ? <span className={MUTED}>{i.floor}</span> : null}
                    {i.needs.length > 0 ? <span className={MUTED}>{t("takeoff.review.links.needs", { defaultValue: "needs {{what}}", what: needsText(i) })}</span> : null}
                  </div>
                  {i.reason ? <p className={MUTED}>{t(`takeoff.review.reason.${i.reason}`, LINK_REASON[i.reason] ?? i.reason)}</p> : null}
                </li>
              ))}
              {open.length > MAX_OPEN_LINKS || data.truncated ? <li className={MUTED}>{t("takeoff.review.links.more", { defaultValue: "and {{n}} more", n: Math.max(0, data.open - MAX_OPEN_LINKS) })}</li> : null}
            </ul>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

interface SteelProps {
  data: SteelRollup | undefined;
  loading: boolean;
  error: boolean;
  inputs: Record<string, string>;
  onInput: (key: string, value: string) => void;
  bad: string[];
}

export function SteelBlock({ data, loading, error, inputs, onInput, bad }: SteelProps) {
  const { t } = useTranslation();
  if (!data && !loading && !error) return null;
  const families = Object.entries(data?.by_family ?? {});
  const without = data?.without_steel.members ?? 0;
  return (
    <section className={BOX} data-testid="review-steel">
      <div className={HEAD}>
        <h3 className={TITLE}>{t("takeoff.review.steel.title", "Steel the members carry")}</h3>
        {data?.ran ? <Badge tone="blue">{kgText(data.kg)}</Badge> : null}
      </div>
      {loading && !data ? <p>{t("takeoff.review.loading", "Checking…")}</p> : null}
      {error && !data ? <p className="text-[var(--color-danger)]">{t("takeoff.review.steel.failed", "Could not add up the steel just now.")}</p> : null}
      {data && !data.ran ? <p data-testid="review-steel-none">{t("takeoff.review.steel.none", "No member carries bars with a size that can be weighed yet.")}</p> : null}
      {families.length > 0 ? (
        <table className="w-full text-left text-[12px]" data-testid="review-steel-table">
          <thead>
            <tr className="text-[var(--color-text-muted)]">
              <th className="font-semibold">{t("takeoff.review.steel.family", "Members")}</th>
              <th className="text-right font-semibold">{t("takeoff.review.steel.weight", "Steel")}</th>
              <th className="text-right font-semibold">{t("takeoff.review.steel.concrete", "Concrete")}</th>
              <th className="text-right font-semibold">kg/m³</th>
            </tr>
          </thead>
          <tbody>
            {families.map(([fam, f]) => (
              <tr key={fam} data-testid={`steel-${fam}`} data-status={f.status ?? ""}>
                <td>{t(`takeoff.review.family.${fam}`, fam.charAt(0) + fam.slice(1).toLowerCase())} <span className={MUTED}>· {f.members}</span></td>
                <td className="text-right">{kgText(f.kg)}</td>
                <td className="text-right">{f.concrete_m3 !== null ? `${f.concrete_m3.toFixed(1)} m³` : "—"}</td>
                <td className="text-right">
                  {f.kg_per_m3 !== null ? <Badge tone={steelTone(f)}>{f.kg_per_m3}</Badge> : "—"}
                  {f.status && f.status !== "IN_RANGE" ? <span className={`block ${MUTED}`}>{t(`takeoff.review.steelStatus.${f.status}`, STEEL_STATUS_LABEL[f.status])} ({rangeText(f)})</span> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {data?.unprinted?.enabled && data.unprinted.members > 0 ? (
        <p data-testid="review-steel-unprinted" className="text-[var(--color-warning)]">
          {t("takeoff.review.steel.unprinted", {
            defaultValue: "{{n}} members print no bars. Estimated, they would add {{kg}} (between {{low}} and {{high}}), {{total}} with the printed bars. This is a guess from their size, not read from the drawing.",
            n: data.unprinted.members,
            kg: kgText(data.unprinted.kg),
            low: kgText(data.unprinted.kg_low),
            high: kgText(data.unprinted.kg_high),
            total: kgText(data.unprinted.kg_with_printed),
          })}
          {Object.keys(data.unprinted.not_estimated).length > 0
            ? ` ${t("takeoff.review.steel.notEstimated", { defaultValue: "Not estimated, size or usual figure missing: {{list}}.", list: Object.entries(data.unprinted.not_estimated).map(([f, n]) => `${f.toLowerCase()} ${n}`).join(", ") })}`
            : ""}
        </p>
      ) : null}
      {without > 0 ? (
        <p data-testid="review-steel-without">
          {t("takeoff.review.steel.without", { defaultValue: "{{n}} members have no bars printed or typed, so they carry no steel here.", n: without })}
          {data && data.without_size > 0 ? ` ${t("takeoff.review.steel.noSize", { defaultValue: "{{n}} more have bars but no size to weigh them by.", n: data.without_size })}` : ""}
        </p>
      ) : null}
      {data ? (
        <details>
          <summary className="cursor-pointer font-semibold text-[var(--color-text-primary)]">{t("takeoff.review.steel.conventions", "Cover, hooks, laps and wastage")}</summary>
          <p className={`mt-1 ${MUTED}`} data-testid="review-steel-note">{data.convention_note}</p>
          <div className="mt-1 grid gap-2 sm:grid-cols-3">
            {STEEL_FIELDS.map((f) => (
              <label key={f.key} className="block">
                <span className="text-[11px] font-semibold text-[var(--color-text-primary)]">{t(`takeoff.review.steel.field.${f.key}`, f.label)}</span>
                <input value={inputs[f.key] ?? ""} placeholder={String(data.conventions[f.key])} inputMode="decimal" aria-label={f.label} onChange={(e) => onInput(f.key, e.target.value)}
                  className="mt-1 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px]" />
                <span className={`block text-[10.5px] ${bad.includes(f.key) ? "text-[var(--color-danger)]" : "text-[var(--color-text-muted)]"}`}>{bad.includes(f.key) ? t("takeoff.review.steel.badValue", "Not a usable value") : f.unit}</span>
              </label>
            ))}
          </div>
        </details>
      ) : null}
    </section>
  );
}

export function ReviewPanel({ drawingId, canEdit = true }: { drawingId: string; canEdit?: boolean }) {
  const { t } = useTranslation();
  const [policy, setPolicy] = useState<Record<string, string>>({});
  const [steelInputs, setSteelInputs] = useState<Record<string, string>>({});
  const [last, setLast] = useState<CombineResult | undefined>(undefined);
  const [skipped, setSkipped] = useState<Array<{ id: string; message: string }>>([]);
  const { conventions, bad } = useMemo(() => conventionsFromInputs(steelInputs), [steelInputs]);

  const floors = useReviewFloors(drawingId);
  const conflicts = useValueConflicts(drawingId, policy);
  const links = useMemberLinks(drawingId);
  const steel = useSteelRollup(drawingId, bad.length ? {} : conventions);
  const combine = useCombineFloorSources(drawingId);
  const resolve = useResolveConflicts(drawingId);
  const busy = combine.isPending || resolve.isPending;

  return (
    <div className="space-y-3" data-testid="review-panel">
      <div>
        <h3 className="font-[Archivo] text-[13.5px] font-bold text-[var(--color-text-primary)]">{t("takeoff.review.title", "Review before approving")}</h3>
        <p className={MUTED}>{t("takeoff.review.intro", "These are read from the drawing as it stands. Nothing here is accepted or changed until you press a button on it.")}</p>
      </div>
      <FloorsBlock floors={floors.data} canEdit={canEdit} busy={busy} last={last}
        onCombine={() => combine.mutate(undefined, { onSuccess: (r) => setLast(r) })} />
      <ConflictsBlock data={conflicts.data} loading={conflicts.isLoading} error={conflicts.isError} policy={policy} canEdit={canEdit} busy={busy} skipped={skipped}
        onPolicy={(k, v) => setPolicy((s) => ({ ...s, [k]: v }))}
        onApplyPolicy={() => resolve.mutate({ policy, apply_policy: true }, { onSuccess: (r) => setSkipped(r.skipped) })}
        onChoose={(id, value) => resolve.mutate({ policy, choices: { [id]: value } }, { onSuccess: (r) => setSkipped(r.skipped) })}
        onChooseDecision={(id, value) => resolve.mutate({ policy, decisions: { [id]: value } }, { onSuccess: (r) => setSkipped(r.skipped) })} />
      {resolve.isError || combine.isError ? <p className="text-[var(--color-danger)]">{t("takeoff.review.failed", "That did not go through. What was done is kept. Try again.")}</p> : null}
      <LinksBlock data={links.data} loading={links.isLoading} error={links.isError} />
      <SteelBlock data={steel.data} loading={steel.isLoading} error={steel.isError} inputs={steelInputs} bad={bad}
        onInput={(k, v) => setSteelInputs((s) => ({ ...s, [k]: v }))} />
    </div>
  );
}
