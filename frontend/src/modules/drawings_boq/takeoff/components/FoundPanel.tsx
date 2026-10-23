import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, inputClass } from "../../../organizations/components/OrganizationUi";
import type { CandidateList, TakeoffCandidate, TakeoffSheet, TypedValue } from "../types/takeoff.types";
import {blockedByHeight, confidenceLevel, factLine, fieldsStillNeeded, groupByKind, isMeasuredBeam, HEIGHT_LABEL, neckHeightAssumed, neededHeights, notMeasurable, staleText, unknownWorkItem, validHeight,
} from "../utils/candidates";
import type { Heights } from "../utils/candidates";
import { groupByFloor, metres, setAsideBy } from "../utils/floorSources";
import { offerText, offersFor } from "../utils/typedMemory";
import { isTankItem, offersSectionChoice, sectionLabel, sectionOptions, tankSizeChoices } from "../utils/choices";
import { SteelEditor } from "./SteelEditor";
import type { SteelSet } from "../utils/steel";

interface Props {
  sheet: TakeoffSheet;
  data: CandidateList | undefined;
  loading: boolean;
  loadError: string | null;
  onRetryLoad: () => void;
  canEdit: boolean;
  scaleReady: boolean;
  scaleRecommended: boolean;
  reading: boolean;
  readError: string | null;
  busy: boolean;
  blocked: string | null;
  selected: Set<string>;
  onSelected: (next: Set<string>) => void
  focusId: string | null;
  heights: Heights;
  onHeights: (next: Heights) => void;
  
  memory?: TypedValue[];
  workItems: Record<string, string>;
  onWorkItems: (next: Record<string, string>) => void;
  workItemCodes: string[];
  onRead: (autoCalibrate: boolean) => void;
  onGoScale: () => void;
  onShow: (c: TakeoffCandidate) => void;
  steel?: Record<string, SteelSet>;
  onSteel?: (id: string, steel: SteelSet | null) => void;
  picks?: Record<string, string>;
  onPick?: (id: string, mark: string | null) => void;
  onAccept: (ids: string[]) => void;
  onReject: (ids: string[]) => void;
 onRestore: (ids: string[]) => void;
  onOpenMeasurement: (measurementId: string) => void;
}

function wallMetres(list: TakeoffCandidate[]): number {
  return list.reduce((sum, c) => sum + (c.category === "WALL" ? Number((c.facts as { length_cc_m?: number }).length_cc_m ?? 0) || 0 : 0), 0);
}

const LEVEL_TONE = { high: "green", medium: "gold", low: "red" } as const;

export function FoundPanel(p: Props) {
  const { t } = useTranslation();
  const data = p.data;
  const ran = Boolean(data?.extraction.ran);

  if (p.sheet.content_kind === "RASTER") {
    return <EmptyState icon="info" title={t("boq.takeoff.found.rasterTitle", "This sheet is a scan")} description={t("boq.takeoff.found.rasterDesc", "There are no drawing lines or text to read. Measure it by hand with the tools above.")} />;
  }
  if (p.loading) return <div className="p-4 text-[13px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.loading", "Loading…")}</div>;
  if (p.loadError) {
    return (
      <div className="space-y-2 p-4 text-[13px]" data-testid="found-error">
        <div className="rounded-[8px] bg-[var(--color-danger-bg)] p-2.5 text-[var(--color-danger)]">{p.loadError}</div>
        <Button size="sm" onClick={p.onRetryLoad}>{t("boq.takeoff.retry", "Read again")}</Button>
      </div>
    );
  }

  if (!ran) {
    return (
      <div className="space-y-3 p-4" data-testid="found-start">
        <p className="text-[13px] text-[var(--color-text-secondary)]">{t("boq.takeoff.found.intro", "Trace can read this drawing and list the walls, columns, doors, windows and rooms it finds. You check the list, then accept what is right.")}</p>
        {p.readError ? <div className="rounded-[8px] bg-[var(--color-danger-bg)] p-2.5 text-[12.5px] text-[var(--color-danger)]" data-testid="found-read-error">{p.readError}</div> : null}
        {p.reading ? (
          <div className="rounded-[8px] bg-[var(--color-info-bg)] p-2.5 text-[13px]" data-testid="found-reading">{t("boq.takeoff.found.reading", "Reading the drawing…")}</div>
        ) : !p.scaleReady ? (
          <>
            <div className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]">{t("boq.takeoff.found.needScale", "Sizes depend on the scale, so the scale of this sheet must be set first.")}</div>
            {p.canEdit && p.scaleRecommended ? (
              <Button variant="primary" onClick={() => p.onRead(true)} data-testid="found-auto-scale">{t("boq.takeoff.found.useScale", "Use the recommended scale and find items")}</Button>
            ) : null}
            <Button onClick={p.onGoScale} data-testid="found-go-scale">{t("boq.takeoff.found.goScale", "Set the scale")}</Button>
          </>
        ) : p.canEdit ? (
          <Button variant="primary" onClick={() => p.onRead(false)} data-testid="found-read">{t("boq.takeoff.found.find", "Find items")}</Button>
        ) : (
          <div className="text-[12.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.notRun", "Nobody has read this sheet yet. Ask someone who can edit the BOQ.")}</div>
        )}
      </div>
    );
  }

  return <FoundList {...p} data={data as CandidateList} />;
}

function FoundList(p: Props & { data: CandidateList }) {
  const { t } = useTranslation();
  const { data } = p;
  const fresh = useMemo(() => data.candidates.filter((c) => c.decision === "NEW"), [data.candidates]);
  const done = useMemo(() => data.candidates.filter((c) => c.decision === "ACCEPTED"), [data.candidates]);
  const rejected = useMemo(() => data.candidates.filter((c) => c.decision === "REJECTED"), [data.candidates]);
  const floorGroups = useMemo(() => groupByFloor(fresh), [fresh]);
  const needed = useMemo(() => neededHeights(fresh, p.picks), [fresh, p.picks]);
  const neckText = useMemo(() => neckHeightAssumed(fresh), [fresh]);
  const tankSizes = useMemo(() => tankSizeChoices(fresh), [fresh]);
  const tankFields = useMemo(() => new Set(fresh.filter(isTankItem).flatMap((c) => fieldsStillNeeded(c, p.picks))), [fresh, p.picks]);
  const chosen = useMemo(() => fresh.filter((c) => p.selected.has(c.id)), [fresh, p.selected]);
  const pending = blockedByHeight(fresh, p.selected, p.heights, p.picks);
  const refused = chosen.filter(notMeasurable);
  const ready = chosen.length - refused.length - pending.length;
  const toggle = (id: string) => {
   const next = new Set(p.selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    p.onSelected(next);
  };
  const setMany = (list: TakeoffCandidate[], on: boolean) => {
    const next = new Set(p.selected);
    for (const c of list) {
      if (on) next.add(c.id);
      else next.delete(c.id);
    }
    p.onSelected(next);
  };
  const canAct = p.canEdit && !p.blocked;

  return (
    <div className="flex min-h-full flex-col" data-testid="found-panel">
      <div className="space-y-3 p-4">
        <div className="flex items-center gap-2">
          <div className="text-[13px] font-semibold" data-testid="found-summary">
            {fresh.length} {t("boq.takeoff.found.toCheck", "to check")} · {done.length} {t("boq.takeoff.found.accepted", "accepted")}
            {rejected.length ? ` · ${rejected.length} ${t("boq.takeoff.found.rejected", "rejected")}` : ""}
          </div>
          {p.canEdit ? (
            <Button size="sm" variant="ghost" className="ml-auto" disabled={p.reading} onClick={() => p.onRead(false)} data-testid="found-reread">
              {p.reading ? t("boq.takeoff.found.reading", "Reading the drawing…") : t("boq.takeoff.found.again", "Read again")}
            </Button>
          ) : null}
        </div>
        <p className="text-[12px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.note", "These were read from the drawing by rules, not typed by a person. Check each one. Accepting makes a draft measurement; nothing counts in the BOQ until you confirm it in the List tab.")}</p>
        {p.readError ? <div className="rounded-[8px] bg-[var(--color-danger-bg)] p-2.5 text-[12.5px] text-[var(--color-danger)]">{p.readError}</div> : null}
        {data.extraction.stale ? (
          <div className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]" data-testid="found-stale">
            {staleText(data.extraction.stale_reasons)} {t("boq.takeoff.found.staleHint", "Read again to refresh the items you have not accepted.")}
          </div>
        ) : null}
        {data.extraction.scale_unverified ? (
          <div className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]">{t("boq.takeoff.found.unverified", "The scale of this sheet is not checked against a printed dimension. Add a check dimension on the Scale tab for better confidence.")}</div>
        ) : null}
        {data.extraction.notes.map((n) => (
          <div key={n.code} className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]">{n.message}</div>
        ))}
        {p.blocked ? <div className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]">{p.blocked}</div> : null}
      </div>

      {needed.length > 0 ? (
        <div className="mx-4 mb-3 rounded-[8px] border border-[var(--color-border)] p-3" data-testid="found-heights">
          <div className="mb-2 text-[12px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.found.heightsTitle", "Needed to measure")}</div>
          <div className="space-y-2">
            {needed.map((f) => {
              const bad = p.heights[f].trim() !== "" && validHeight(p.heights[f]) === null;
              return (
                <label key={f} className="block text-[12.5px]">
                  <span className="mb-1 block font-medium">{t(`boq.takeoff.found.height.${f}`, HEIGHT_LABEL[f])}</span>
                  <input
                    className={inputClass}
                    inputMode="decimal"
                    value={p.heights[f]}
                    placeholder="e.g. 3000"
                    data-testid={`found-height-${f}`}
                    onChange={(e) => p.onHeights({ ...p.heights, [f]: e.target.value })}
                  />
                  {bad ? <span className="mt-0.5 block text-[11.5px] text-[var(--color-danger)]">{t("boq.takeoff.found.heightBad", "Type a number between 100 and 20000.")}</span> : null}
                  {offersFor(f, fresh, p.memory, p.picks).filter((o) => String(o.mm) !== p.heights[f].trim()).length > 0 ? (
                    <span className="mt-1 flex flex-wrap items-center gap-1" data-testid={`found-last-${f}`}>
                      <span className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.lastTyped", "Typed before in this project (tap to use):")}</span>
                      {offersFor(f, fresh, p.memory, p.picks).filter((o) => String(o.mm) !== p.heights[f].trim()).map((o) => (
                        <button key={o.mm} type="button" className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[11.5px] hover:border-[var(--color-trace-gold)]" data-testid={`found-last-${f}-${o.mm}`}
                          onClick={() => p.onHeights({ ...p.heights, [f]: String(o.mm) })}>{offerText(o)}</button>
                      ))}
                    </span>
                  ) : null}
                  {(f === "tank_wall_height_mm" || tankFields.has(f)) && tankSizes.length > 0 ? (
                    <span className="mt-1 flex flex-wrap items-center gap-1" data-testid="found-tank-sizes">
                      <span className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.tankSizes", "Printed on the tank drawings (the drawing does not say which is the inside depth; tap one to use it):")}</span>
                      {tankSizes.map((sz) => (
                        <button key={sz.mm} type="button" className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[11.5px] hover:border-[var(--color-trace-gold)]" data-testid={`found-tank-size-${sz.mm}`}
                          onClick={() => p.onHeights({ ...p.heights, [f]: String(sz.mm) })}>{sz.text}</button>
                      ))}
                    </span>
                  ) : null}
                </label>
              );
            })}
          </div>
          <div className="mt-2 text-[11.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.heightsHint", "The drawing gave no value for these. They are saved on each accepted item as given by you.")}</div>
        </div>
) : null}

      {neckText !== null && !needed.includes("neck_height_mm") ? (
        <div className="mx-4 mb-3 rounded-[8px] border border-[var(--color-border)] p-3" data-testid="found-neck-override">
          <label className="block text-[12.5px]">
            <span className="mb-1 block font-medium">{t("boq.takeoff.found.neckOverride", { defaultValue: "Neck column height: {{text}} is used, as in the QS's workbook, and is marked assumed. Type another height to use instead (mm).", text: neckText })}</span>
            <input className={inputClass} inputMode="decimal" value={p.heights.neck_height_mm} placeholder={t("boq.takeoff.found.neckPlaceholder", "optional")} data-testid="found-height-neck_height_mm"
              onChange={(e) => p.onHeights({ ...p.heights, neck_height_mm: e.target.value })} />
            {p.heights.neck_height_mm.trim() !== "" && validHeight(p.heights.neck_height_mm) === null ? (
              <span className="mt-0.5 block text-[11.5px] text-[var(--color-danger)]">{t("boq.takeoff.found.heightBad", "Type a number between 100 and 20000.")}</span>
            ) : null}
          </label>
        </div>
      ) : null}

      {fresh.length === 0 ? (
        <div className="px-4 pb-4 text-[13px] text-[var(--color-text-muted)]" data-testid="found-none-left">
          {data.candidates.length === 0 ? t("boq.takeoff.found.nothing", "Nothing could be read from this sheet. Measure it by hand with the tools above.") : t("boq.takeoff.found.allDone", "Everything found has been accepted or rejected.")}        </div>
      ) : null}

      <div className="space-y-5 px-4 pb-4">
        {floorGroups.map((fg) => (
        <div key={fg.key || "all"} className="space-y-4" data-testid={fg.key ? `found-floor-${fg.key}` : undefined}>
        {fg.key ? (
          <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-1">
            {p.canEdit ? <input type="checkbox" aria-label={t("boq.takeoff.found.selectFloor", "Select all of {{what}}", { what: fg.title })} checked={fg.items.every((c) => p.selected.has(c.id))} onChange={() => setMany(fg.items, !fg.items.every((c) => p.selected.has(c.id)))} /> : null}
            <h2 className="text-[13px] font-semibold">{fg.title}</h2>
            <span className="text-[11.5px] text-[var(--color-text-muted)]">{fg.items.length} {t("boq.takeoff.found.toCheck", "to check")}{wallMetres(fg.items) > 0 ? ` · ${metres(wallMetres(fg.items))} ${t("boq.takeoff.found.ofWall", "of wall")}` : ""}</span>
          </div>
        ) : null}
        {groupByKind(fg.items).map((g) => {
          const allOn = g.items.every((c) => p.selected.has(c.id));
          const code = p.workItems[g.key] ?? "";
          const suggested = g.items.find((c) => c.suggested_work_item)?.suggested_work_item ?? null;
          const unknown = unknownWorkItem(code, p.workItemCodes);
          return (
            <section key={g.key} data-testid={`found-group-${g.key}`}>
              <div className="mb-1.5 flex items-center gap-2">
                {p.canEdit ? <input type="checkbox" aria-label={t("boq.takeoff.found.selectGroup", "Select all {{what}}", { what: g.title })} checked={allOn} onChange={() => setMany(g.items, !allOn)} /> : null}
                <h3 className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{g.title} ({g.items.length})</h3>
                {g.key !== "BEAM" && p.canEdit ? (
                  <input
                    className={`${inputClass} ml-auto !h-7 !w-[130px] !px-2 !text-[12px] ${unknown ? "!border-[var(--color-danger)]" : ""}`}
                    list="found-work-items"
                    value={code}
                    placeholder={suggested ?? t("boq.takeoff.found.workItem", "Work item")}
                    title={t("boq.takeoff.found.workItemTip", "Work item for the {{what}} you accept. Leave empty to use the suggestion.", { what: g.title.toLowerCase() })}
                    data-testid={`found-workitem-${g.key}`}
                    onChange={(e) => p.onWorkItems({ ...p.workItems, [g.key]: e.target.value.toUpperCase() })}
                  />
                ) : null}
              </div>
              {unknown ? <div className="mb-1.5 text-[11.5px] text-[var(--color-danger)]" data-testid={`found-workitem-bad-${g.key}`}>{t("boq.takeoff.found.workItemUnknown", "{{code}} is not a work item in your catalog. Pick one from the list.", { code })}</div> : null}
              {!suggested && !code && g.key !== "BEAM" && p.canEdit ? <div className="mb-1.5 text-[11.5px] text-[var(--color-text-muted)]" data-testid={`found-workitem-none-${g.key}`}>{t("boq.takeoff.found.workItemNone", "No work item is proposed for these. Choose one above, or choose it later when you build the bill.")}</div> : null}
              <ul className="space-y-1.5">
                {g.items.map((c) => (
                  <Row key={c.id} c={c} steel={p.steel?.[c.id]} onSteel={p.onSteel} pick={p.picks?.[c.id]} onPick={p.onPick} selected={p.selected.has(c.id)} focused={p.focusId === c.id} canEdit={p.canEdit} onToggle={() => toggle(c.id)} onShow={() => p.onShow(c)} onReject={() => p.onReject([c.id])} />
                ))}
              </ul>
            </section>
          );
        })}
        </div>
        ))}
      </div>
      <datalist id="found-work-items">{p.workItemCodes.map((c) => <option key={c} value={c} />)}</datalist>

      {done.length > 0 ? (
        <details className="px-4 pb-3" data-testid="found-accepted">
          <summary className="cursor-pointer text-[12.5px] font-semibold">{t("boq.takeoff.found.acceptedTitle", "Accepted")} ({done.length})</summary>
          <ul className="mt-1.5 space-y-1">
            {done.map((c) => (
              <li key={c.id} className="flex items-center gap-2 rounded-[8px] border border-[var(--color-border)] px-2.5 py-1.5 text-[12.5px]">
                <span className="truncate">{c.label}</span>
                {c.measurement_id ? <Button size="sm" variant="ghost" className="ml-auto" onClick={() => p.onOpenMeasurement(c.measurement_id as string)}>{t("boq.takeoff.found.open", "Open")}</Button> : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {rejected.length > 0 ? (
        <details className="px-4 pb-3" data-testid="found-rejected">
          <summary className="cursor-pointer text-[12.5px] font-semibold">{t("boq.takeoff.found.rejectedTitle", "Rejected")} ({rejected.length})</summary>
          <ul className="mt-1.5 space-y-1">
            {rejected.map((c) => (
              <li key={c.id} className="flex items-center gap-2 rounded-[8px] border border-[var(--color-border)] px-2.5 py-1.5 text-[12.5px]">
                <span className="truncate text-[var(--color-text-secondary)]">{c.label}</span>
                {setAsideBy(c) !== null ? <Badge tone="slate">{t("boq.takeoff.found.setAside", "set aside: page {{n}} is in use", { n: setAsideBy(c) })}</Badge> : null}
                {p.canEdit ? <Button size="sm" variant="ghost" className="ml-auto" onClick={() => p.onRestore([c.id])}>{t("boq.takeoff.found.restore", "Restore")}</Button> : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {data.extraction.unmapped_tags.length > 0 ? (
        <div className="px-4 pb-3 text-[12px] text-[var(--color-text-muted)]" data-testid="found-unmapped">
          {t("boq.takeoff.found.unmapped", "Marks on the sheet that were not recognised")}: {data.extraction.unmapped_tags.map((u) => `${u.tag} ×${u.count}`).join(", ")}. {t("boq.takeoff.found.unmappedHint", "Count them from the Counts tab.")}
        </div>
      ) : null}

      {fresh.length > 0 && p.canEdit ? (
        <div className="sticky bottom-0 mt-auto border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3" data-testid="found-actions">
          <div className="mb-2 flex items-center gap-2 text-[12px] text-[var(--color-text-secondary)]">
            <button type="button" className="underline" onClick={() => setMany(fresh.filter((c) => !notMeasurable(c)), true)} data-testid="found-select-all">{t("boq.takeoff.found.selectAll", "Select all")}</button>
            <button type="button" className="underline" onClick={() => p.onSelected(new Set())}>{t("boq.takeoff.found.clear", "Clear")}</button>
            <span className="ml-auto">{chosen.length} {t("boq.takeoff.found.selected", "selected")}</span>
          </div>
          {pending.length > 0 ? <div className="mb-2 text-[11.5px] text-[var(--color-warning)]">{t("boq.takeoff.found.needHeights", "Type the heights above to accept {{n}} of the selected items.", { n: pending.length })}</div> : null}
          {refused.length > 0 ? <div className="mb-2 text-[11.5px] text-[var(--color-warning)]">{t("boq.takeoff.found.skipped", "{{n}} selected item(s) cannot be measured automatically and will be skipped.", { n: refused.length })}</div> : null}
          <div className="flex gap-2">
            <Button variant="primary" className="flex-1" disabled={!canAct || p.busy || ready <= 0} onClick={() => p.onAccept(chosen.filter((c) => !notMeasurable(c) && !pending.includes(c)).map((c) => c.id))} data-testid="found-accept">
              {t("boq.takeoff.found.accept", "Accept")} {ready > 0 ? ready : ""}
            </Button>
            <Button disabled={!canAct || p.busy || chosen.length === 0} onClick={() => p.onReject(chosen.map((c) => c.id))} data-testid="found-reject">{t("boq.takeoff.found.reject", "Reject")}</Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Row({ c, steel, onSteel, pick, onPick, selected, focused, canEdit, onToggle, onShow, onReject }: {
  c: TakeoffCandidate; steel?: SteelSet; onSteel?: (id: string, steel: SteelSet | null) => void; pick?: string; onPick?: (id: string, mark: string | null) => void; selected: boolean; focused: boolean; canEdit: boolean; onToggle: () => void; onShow: () => void; onReject: () => void;
}) {
  const { t } = useTranslation();
  const level = confidenceLevel(c.confidence);
  // The unchecked-scale warning applies to the whole sheet and is shown once at the top, not on every row.
  const warnings = c.notes.filter((n) => n.severity !== "info" && n.code !== "SCALE_UNVERIFIED");
  const infos = c.notes.filter((n) => n.severity === "info");
  const facts = factLine(c);
  const unmeasurable = notMeasurable(c);
  return (
    <li className={`rounded-[8px] border p-2.5 ${focused ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"}`} data-testid="found-row" data-category={c.category} data-selected={selected}>
      <div className="flex items-start gap-2">
        {canEdit ? <input type="checkbox" className="mt-1" checked={selected} disabled={unmeasurable} onChange={onToggle} aria-label={c.label} /> : null}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-[13px] font-semibold">{c.label}</span>
            <Badge tone={LEVEL_TONE[level]}>{Math.round(Number(c.confidence) * 100)}%</Badge>
            {warnings.length > 0 ? <Badge tone="gold">{t("boq.takeoff.found.check", "check")}</Badge> : null}
            {c.missing.includes("size") ? <Badge tone="red">{t("boq.takeoff.found.noSize", "no size")}</Badge> : null}
            {c.category === "BEAM" && !isMeasuredBeam(c) ? <Badge tone="slate">{t("boq.takeoff.found.countOnly", "count only")}</Badge> : null}
          </div>
          {facts ? <div className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]">{facts}</div> : null}
          {warnings.map((n) => <div key={n.code} className="mt-1 text-[11.5px] text-[var(--color-warning)]">{n.message}</div>)}
          {infos.length > 0 ? (
            <details className="mt-1">
              <summary className="cursor-pointer text-[11.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.found.more", "More")}</summary>
              {infos.map((n) => <div key={n.code} className="mt-0.5 text-[11.5px] text-[var(--color-text-secondary)]">{n.message}</div>)}
            </details>
          ) : null}
          {onPick && canEdit && offersSectionChoice(c) ? (
            <label className="mt-1.5 block text-[11.5px]" data-testid="found-section-pick">
              <span className="mb-0.5 block text-[var(--color-text-muted)]">{(c.facts as Record<string, unknown> | null)?.from_strips === true
                ? t("boq.takeoff.found.sectionPickStrip", "No section is captioned with this beam's mark. These are the sections printed for this kind of beam. Choose one, or type a depth above.")
                : t("boq.takeoff.found.sectionPick", "The sheet prints several sections for this kind of beam and does not say which lies under which wall. Choose one, or type a depth above.")}</span>
              <select className={`${inputClass} !h-8 !px-2 !text-[12px]`} value={pick ?? ""} data-testid="found-section-select" onChange={(e) => onPick(c.id, e.target.value || null)}>
                <option value="">{t("boq.takeoff.found.sectionNone", "Choose a section…")}</option>
                {sectionOptions(c).map((o) => <option key={o.mark} value={o.mark}>{sectionLabel(o)}</option>)}
              </select>
            </label>
          ) : null}
          {onSteel && !unmeasurable ? <SteelEditor c={c} typed={steel} canEdit={canEdit} onChange={onSteel} /> : null}
          <div className="mt-1.5 flex gap-2">
            <Button size="sm" variant="ghost" onClick={onShow} data-testid="found-show">{t("boq.takeoff.counts.show", "Show")}</Button>
            {canEdit ? <Button size="sm" variant="ghost" onClick={onReject}>{t("boq.takeoff.found.reject", "Reject")}</Button> : null}
          </div>
        </div>
      </div>
    </li>
  );
}
