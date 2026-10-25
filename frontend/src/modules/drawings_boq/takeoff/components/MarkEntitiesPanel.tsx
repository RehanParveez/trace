import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import type { MarkChoiceBody, MarkEntities, MarkEntity } from "../types/markEntities.types";
import { floorName } from "../utils/floorSources";
import { markState, markTitle, sourceLine } from "../utils/markEntities";

interface Props {
  data: MarkEntities | undefined;
  canEdit: boolean;
  busy: boolean;
  currentSheetId: string;
  onChoose: (body: MarkChoiceBody) => void;
  onOpenSheet: (sheetId: string) => void;
}

export function MarkEntitiesPanel(p: Props) {
  const { t } = useTranslation();
  const entities = p.data?.entities ?? [];
  if (entities.length === 0) return null;
  const toDecide = p.data?.to_decide ?? 0;
  const differ = p.data?.differ ?? 0;
  const unplaced = p.data?.unplaced ?? 0;
  const same = toDecide - differ;
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="mark-entities" data-to-decide={toDecide}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.marks.title", "Marks shown on more than one sheet")}</h3>
        {toDecide > 0 ? <Badge tone="gold">{t("boq.takeoff.marks.toDecide", "{{n}} to decide", { n: toDecide })}</Badge> : <Badge tone="green">{t("boq.takeoff.marks.decided", "all decided")}</Badge>}
        {unplaced > 0 ? <Badge tone="slate">{t("boq.takeoff.marks.unplaced", "{{n}} with no floor named", { n: unplaced })}</Badge> : null}
      </div>
      {toDecide > 0 ? (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]">
          {t("boq.takeoff.marks.help", "The same column, footing, opening, lintel, stair, beam or site mark of one floor is shown on more than one sheet. A mark is counted from one sheet only: the items of the other sheets are held back from the bulk accept until you choose. Where the sheets show the same count and size the suggested sheet (a schedule before a detail before a plan label, then a sheet that names its floor) is ready; where they differ nothing is ready until you choose. The sheets you do not choose are set aside, and you can change your mind.")}
        </p>
      ) : null}
      {same > 0 && p.canEdit ? (
        <Button size="sm" variant="primary" disabled={p.busy} onClick={() => p.onChoose({ use_suggested: true })} data-testid="mark-entities-suggested">
          {same === 1 ? t("boq.takeoff.marks.useSuggestedOne", "Use the suggested sheet") : t("boq.takeoff.marks.useSuggested", "Use the suggested sheet for the {{n}} marks that agree", { n: same })}
        </Button>
      ) : null}
      <ul className="space-y-2">
        {entities.map((e) => <EntityRow key={e.key} e={e} p={p} />)}
      </ul>
    </section>
  );
}

function EntityRow({ e, p }: { e: MarkEntity; p: Props }) {
  const { t } = useTranslation();
  const state = markState(e);
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`mark-entity-${e.key}`} data-state={e.state} data-category={e.category}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{markTitle(e)}</span>
        <span className="text-[11.5px] text-[var(--color-text-secondary)]">{e.floor ? floorName(e.floor) : e.category === "SITE" ? t("boq.takeoff.marks.site", "Site") : t("boq.takeoff.marks.floorUnknown", "Floor not named")}</span>
        <Badge tone={state.tone}>{state.text}</Badge>
      </div>
      <ul className="mt-1 space-y-1">
        {e.sources.map((s) => {
          const inUse = e.state === "CHOSEN" && e.chosen_sheet_id === s.sheet_id;
          const here = s.sheet_id === p.currentSheetId;
          const away = s.set_aside > 0 && s.open + s.accepted === 0;
          return (
            <li key={s.sheet_id} className="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid={`mark-source-${e.key}-${s.page_no}`} data-in-use={inUse}>
              <span className={away ? "text-[var(--color-text-muted)] line-through" : ""}>{t("boq.takeoff.marks.page", "Page {{n}}", { n: s.page_no })}{s.caption ? ` · ${s.caption}` : ""}</span>
              <span className="text-[11.5px] text-[var(--color-text-secondary)]">{sourceLine(s)}</span>
              {e.suggested_sheet_id === s.sheet_id && e.state === "DOUBLE" ? <Badge tone="blue">{t("boq.takeoff.marks.suggested", "suggested")}</Badge> : null}
              <span className="ml-auto flex items-center gap-1">
                {e.choosable && p.canEdit && !inUse ? (
                  <Button size="sm" disabled={p.busy} onClick={() => p.onChoose({ choices: [{ key: e.key, sheet_id: s.sheet_id }] })} data-testid={`mark-use-${e.key}-${s.page_no}`}>
                    {t("boq.takeoff.marks.use", "Use page {{n}}", { n: s.page_no })}
                  </Button>
                ) : null}
                {!here ? <Button size="sm" variant="ghost" onClick={() => p.onOpenSheet(s.sheet_id)}>{t("boq.takeoff.marks.open", "Open")}</Button> : null}
              </span>
            </li>
          );
        })}
      </ul>
      {e.conflict ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-danger)]" data-testid={`mark-conflict-${e.key}`}>
          {t("boq.takeoff.marks.conflict", "Two of these sheets already have this mark accepted. Delete the measurement of one of them, then choose the other sheet.")}
        </p>
      ) : null}
    </li>
  );
}
