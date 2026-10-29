import { useTranslation } from "react-i18next";
import { Badge, useToast } from "../../../../organizations/components/OrganizationUi";
import { takeoffErrorMessage } from "../../utils/errors";
import { useChooseDecision, useDecisions, useReadAfterDecision } from "../hooks/useDecisions";
import { diffText, figureText, pagesText, shown, summaryLine } from "../utils/decisions";
import { factSourcesText, TRUST_LABEL } from "../../utils/review";
import { CandidateCrop } from "../../crops/components/CandidateCrop";
import type { TakeoffCandidate } from "../../types/takeoff.types";
import type { DecisionItem, DecisionOption, FactDecisionItem, SheetDecision } from "../types/decisions.types";

interface Props {
  drawingId: string;
  canEdit: boolean;
  version?: number;
}

const BTN = "rounded-[8px] border border-[var(--color-border)] px-2 py-0.5 text-[11.5px] disabled:opacity-50";
const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";

function Option({ item, o, name, disabled, onPick }: { item: DecisionItem; o: DecisionOption; name: string; disabled: boolean; onPick: (value: string) => void }) {
  const { t } = useTranslation();
  const figures = o.effect?.figures ?? [];
  const diff = o.in_force ? "" : diffText(o.effect);
  return (
    <li>
      <label className={`flex cursor-pointer items-start gap-2 rounded-[8px] border p-2 ${o.in_force ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"}`} data-testid={`decision-${item.key}-${o.value}`} data-in-force={o.in_force}>
        <input type="radio" name={name} className="mt-0.5" checked={o.in_force} disabled={disabled} onChange={() => onPick(o.value)} />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{t(`boq.takeoff.decisions.option.${o.value}`, o.label)}</span>
            {o.is_default ? <span className={MUTED}>{t("boq.takeoff.decisions.default", "default")}</span> : null}
            {diff ? <Badge tone="slate">{diff}</Badge> : null}
          </span>
          <span className={`block ${MUTED}`}>{o.text}</span>
          {figures.length ? <span className="block text-[11.5px]" data-testid={`decision-${item.key}-${o.value}-figures`}>{figures.map(figureText).join(" · ")}</span> : null}
        </span>
      </label>
    </li>
  );
}

function Item({ item, canEdit, busy, onChoose, onRead, reading }: {
  item: DecisionItem; canEdit: boolean; busy: boolean; reading: boolean; onChoose: (key: string, value: string | null) => void; onRead: () => void;
}) {
  const { t } = useTranslation();
  const late = item.stale_pages.length > 0;
  return (
    <li className="space-y-2 rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`decision-${item.key}`} data-chosen={item.made_by_person} data-stale={late}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{t(`boq.takeoff.decisions.title.${item.key}`, item.title)}</span>
        <Badge tone={item.made_by_person ? "green" : "gold"}>
          {item.made_by_person ? t("boq.takeoff.decisions.yours", "Your choice") : t("boq.takeoff.decisions.assumed", "Default, assumed")}
        </Badge>
        <span className={MUTED}>{item.rule}</span>
        {item.made_by_person && canEdit ? (
          <button type="button" className={`${BTN} ml-auto`} disabled={busy} onClick={() => onChoose(item.key, null)} data-testid={`decision-${item.key}-reset`}>
            {t("boq.takeoff.decisions.reset", "Back to the default")}
          </button>
        ) : null}
      </div>
      <p className={MUTED}>{item.question}</p>
      <ul className="list-none space-y-1.5 pl-0">
        {item.options.map((o) => <Option key={o.value} item={item} o={o} name={`decision-${item.key}`} disabled={!canEdit || busy} onPick={(v) => onChoose(item.key, v)} />)}
      </ul>
      {!item.applies ? <p className={MUTED}>{t("boq.takeoff.decisions.nothing", "Nothing read from this drawing depends on this choice.")}</p> : (
        <p className={MUTED}>{t("boq.takeoff.decisions.affects", "Changes: {{what}}.", { what: item.affects })}</p>
      )}
      {late ? (
        <div className="flex flex-wrap items-center gap-2 rounded-[8px] bg-[var(--color-surface-muted)] p-2" data-testid={`decision-${item.key}-stale`}>
          <span className="text-[11.5px]">
            {t("boq.takeoff.decisions.stale", "{{n}} sheets were read before this choice ({{pages}}). Read them again to apply it.", { n: item.stale_pages.length, pages: pagesText(item.stale_pages) })}
            {item.accepted_stale ? " " + t("boq.takeoff.decisions.keptAccepted", "{{n}} items already accepted from them keep the value they were accepted with.", { n: item.accepted_stale }) : ""}
          </span>
          {canEdit ? <button type="button" className={BTN} disabled={reading || busy} onClick={onRead}>{reading ? t("boq.takeoff.decisions.reading", "Reading…") : t("boq.takeoff.decisions.read", "Read them again")}</button> : null}
        </div>
      ) : null}
    </li>
  );
}

function FactItem({ d, canEdit, busy, onPick }: { d: FactDecisionItem; canEdit: boolean; busy: boolean; onPick: (id: string, value: string) => void }) {
  const { t } = useTranslation();
  return (
    <li className="space-y-2 rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`decision-fact-${d.id}`} data-open={d.open}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{t(`boq.takeoff.decisions.fact.${d.kind}`, d.title)}</span>
        <Badge tone={d.open ? "gold" : "green"}>{d.open ? t("boq.takeoff.decisions.open", "Open") : t("boq.takeoff.decisions.yours", "Your choice")}</Badge>
        <span className={MUTED}>{t("boq.takeoff.decisions.factRows", "{{n}} rows: {{facts}}", { n: d.rows, facts: d.facts.slice(0, 4).map((k) => k.split(":").slice(1).join(":") || k).join(", ") + (d.facts.length > 4 ? ` +${d.facts.length - 4}` : "") })}</span>
      </div>
      <p className={MUTED}>{d.question}</p>
      <ul className="list-none space-y-1.5 pl-0">
        {d.options.map((o) => (
          <li key={o.value}>
            <label className={`flex cursor-pointer items-start gap-2 rounded-[8px] border p-2 ${d.chosen === o.value ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"}`} data-testid={`decision-fact-${d.id}-${o.value}`} data-in-force={d.chosen === o.value}>
              <input type="radio" name={`decision-fact-${d.id}`} className="mt-0.5" checked={d.chosen === o.value} disabled={!canEdit || busy} onChange={() => onPick(d.id, o.value)} />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{o.label ?? o.value}</span>
                  {o.trust ? <span className={MUTED}>{TRUST_LABEL[o.trust] ?? o.trust}{o.default ? " · " + t("boq.takeoff.decisions.moreTrusted", "more trusted") : ""}</span> : null}
                  {o.quantity != null ? <span className="text-[11.5px]">{o.quantity.toLocaleString("en-US", { maximumFractionDigits: 2 })} {o.unit ?? ""}</span> : null}
                </span>
                <span className={`block ${MUTED}`}>{factSourcesText(o.sources)}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      {d.open && d.default == null ? <p className={MUTED}>{t("boq.takeoff.decisions.tied", "The sources are equally trusted, so this is left to you.")}</p> : null}
      <p className={MUTED}>{t("boq.takeoff.decisions.affects", "Changes: {{what}}.", { what: d.affects })}</p>
    </li>
  );
}

function SheetItem({ d, canEdit, busy, onPick }: { d: SheetDecision; canEdit: boolean; busy: boolean; onPick: (id: string, value: string) => void }) {
  const { t } = useTranslation();
  const title = d.kind === "OPTION" ? t("boq.takeoff.decisions.option.title", "Which option was built") : t("boq.takeoff.decisions.revision.title", "Which revision is current");
  return (
    <li className="space-y-2 rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`decision-sheets-${d.id}`} data-state={d.state} data-kind={d.kind}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{title}</span>
        <Badge tone={d.state === "CHOSEN" ? "green" : "gold"}>{d.state === "CHOSEN" ? t("boq.takeoff.decisions.sheetChosen", "Chosen") : t("boq.takeoff.decisions.sheetOpen", "Open")}</Badge>
        <span className={MUTED}>{d.caption}{d.sheet_no ? ` · ${d.sheet_no}` : ""}</span>
      </div>
      <p className={MUTED}>{d.question}</p>
      <ul className="list-none space-y-1.5 pl-0">
        {d.options.map((o) => (
          <li key={o.value}>
            <label className={`flex cursor-pointer items-start gap-2 rounded-[8px] border p-2 ${d.chosen === o.value ? "border-[var(--color-trace-gold)]" : "border-[var(--color-border)]"}`} data-testid={`decision-sheets-${d.id}-${o.value}`} data-in-force={d.chosen === o.value}>
              <input type="radio" name={`decision-sheets-${d.id}`} className="mt-0.5" checked={d.chosen === o.value} disabled={!canEdit || busy || !d.choosable} onChange={() => onPick(d.id, o.value)} />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{o.label}</span>
                  {d.default === o.value ? <span className={MUTED}>{t("boq.takeoff.decisions.later", "later, the default")}</span> : null}
                  {o.set_aside ? <span className={MUTED}>{t("boq.takeoff.decisions.setAside", "set aside")}</span> : null}
                </span>
                <span className={`block ${MUTED}`}>{t("boq.takeoff.decisions.sheetPages", "Page {{pages}} · {{n}} items", { pages: o.pages.join(", "), n: o.items })}{o.text && o.text !== o.label ? ` · ${o.text}` : ""}</span>
                {o.sample ? <CandidateCrop c={{ id: o.sample.id, label: o.sample.label ?? "", geometry: o.sample.geometry } as Pick<TakeoffCandidate, "id" | "label" | "geometry">} pageNo={o.pages[0]} /> : null}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </li>
  );
}

export function DecisionsPanel({ drawingId, canEdit, version = 0 }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const report = useDecisions(drawingId, version);
  const choose = useChooseDecision(drawingId);
  const read = useReadAfterDecision(drawingId);
  const data = report.data;
  if (report.isLoading || (report.isError && !data)) return null;
  const items = shown(data);
  const facts = data?.facts ?? [];
  const sheets = data?.sheets ?? [];
  if (!data || !data.sheets_read || (!items.length && !facts.length && !sheets.length)) return null;
  const line = summaryLine(items);
  const onChoose = (key: string, value: string | null) => choose.mutate({ key, value }, {
    onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.decisions.failed", "Could not save the choice"), description: takeoffErrorMessage(e) }),
  });
  const onRead = () => read.mutate(undefined, {
    onSuccess: (r) => showToast({ tone: "success", title: t("boq.takeoff.decisions.readDone", "{{n}} sheets read again", { n: r.done.length }) }),
    onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.decisions.readFailed", "Could not read the sheets again"), description: takeoffErrorMessage(e) }),
  });
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="decisions-panel" data-stale={data.stale_pages.length > 0}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.decisions.heading", "Decisions for this drawing")}</h3>
        {line ? <span className={MUTED}>{line}</span> : null}
      </div>
      <p className={MUTED}>{t("boq.takeoff.decisions.hint", "Each choice changes quantities. The figures under an option are worked out from what has been read of this drawing, so you can see the effect before you choose.")}</p>
      <ul className="list-none space-y-2 pl-0">
        {items.map((i) => <Item key={i.key} item={i} canEdit={canEdit} busy={choose.isPending} reading={read.isPending} onChoose={onChoose} onRead={onRead} />)}
      </ul>
      {sheets.length ? (
        <>
          <h4 className="font-semibold" data-testid="decisions-sheets">{t("boq.takeoff.decisions.sheets", "Options and revisions in this set")}</h4>
          <ul className="list-none space-y-2 pl-0">
            {sheets.map((d) => <SheetItem key={d.id} d={d} canEdit={canEdit} busy={choose.isPending} onPick={(id, value) => choose.mutate({ key: "", decision_id: id, value }, {
              onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.decisions.failed", "Could not save the choice"), description: takeoffErrorMessage(e) }) })} />)}
          </ul>
        </>
      ) : null}
      {facts.length ? (
        <>
          <h4 className="font-semibold" data-testid="decisions-facts">{t("boq.takeoff.decisions.facts", "Values the sheets print differently")}</h4>
          <ul className="list-none space-y-2 pl-0">
            {facts.map((d) => <FactItem key={d.id} d={d} canEdit={canEdit} busy={choose.isPending} onPick={(id, value) => choose.mutate({ key: "", decision_id: id, value }, {
              onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.decisions.failed", "Could not save the choice"), description: takeoffErrorMessage(e) }) })} />)}
          </ul>
        </>
      ) : null}
    </section>
  );
}
