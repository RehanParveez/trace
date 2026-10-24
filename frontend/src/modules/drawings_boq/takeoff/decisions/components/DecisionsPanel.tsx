import { useTranslation } from "react-i18next";
import { Badge, useToast } from "../../../../organizations/components/OrganizationUi";
import { takeoffErrorMessage } from "../../utils/errors";
import { useChooseDecision, useDecisions, useReadAfterDecision } from "../hooks/useDecisions";
import { diffText, figureText, pagesText, shown, summaryLine } from "../utils/decisions";
import type { DecisionItem, DecisionOption } from "../types/decisions.types";

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

export function DecisionsPanel({ drawingId, canEdit, version = 0 }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const report = useDecisions(drawingId, version);
  const choose = useChooseDecision(drawingId);
  const read = useReadAfterDecision(drawingId);
  const data = report.data;
  if (report.isLoading || (report.isError && !data)) return null;
  const items = shown(data);
  if (!data || !data.sheets_read || !items.length) return null;
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
    </section>
  );
}
