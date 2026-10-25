import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import type { LayoutChoiceBody, LayoutGroup, LayoutGroups } from "../types/layoutGroups.types";
import { floorName } from "../utils/floorSources";
import { groupState, groupTitle, sourceLine } from "../utils/layoutGroups";

interface Props {
  data: LayoutGroups | undefined;
  canEdit: boolean;
  busy: boolean;
  currentSheetId: string;
  onChoose: (body: LayoutChoiceBody) => void;
  onOpenSheet: (sheetId: string) => void;
}

export function LayoutGroupsPanel(p: Props) {
  const { t } = useTranslation();
  const groups = p.data?.groups ?? [];
  if (groups.length === 0) return null;
  const toDecide = p.data?.to_decide ?? 0;
  const twice = p.data?.repeated_room_area_m2 ?? 0;
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="layout-groups" data-to-decide={toDecide}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.layouts.title", "Plans printed on more than one sheet")}</h3>
        {toDecide > 0 ? <Badge tone="gold">{t("boq.takeoff.layouts.toDecide", "{{n}} to decide", { n: toDecide })}</Badge> : <Badge tone="green">{t("boq.takeoff.layouts.decided", "all decided")}</Badge>}
      </div>
      {toDecide > 0 ? (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]">
          {t("boq.takeoff.layouts.help", "These sheets carry the same plan: the same named rooms with the same areas ({{m2}} m² would be counted again). The items of all but one are held back from the bulk accept until you choose the sheet that governs. The other sheets are set aside, and you can change your mind.", { m2: twice.toLocaleString("en", { maximumFractionDigits: 1 }) })}
        </p>
      ) : null}
      {toDecide > 0 && p.canEdit ? (
        <Button size="sm" variant="primary" disabled={p.busy} onClick={() => p.onChoose({ use_suggested: true })} data-testid="layout-groups-suggested">
          {toDecide === 1 ? t("boq.takeoff.layouts.useSuggestedOne", "Use the suggested sheet") : t("boq.takeoff.layouts.useSuggested", "Use the suggested sheet for all {{n}} plans", { n: toDecide })}
        </Button>
      ) : null}
      <ul className="space-y-2">
        {groups.map((g) => <GroupRow key={g.key} g={g} p={p} />)}
      </ul>
    </section>
  );
}

function GroupRow({ g, p }: { g: LayoutGroup; p: Props }) {
  const { t } = useTranslation();
  const state = groupState(g);
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`layout-group-${g.key}`} data-state={g.state} data-kind={g.kind}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{g.floor ? floorName(g.floor) : t("boq.takeoff.layouts.floorUnknown", "Floor not named on the sheets")}</span>
        <span className="text-[11.5px] text-[var(--color-text-secondary)]">{groupTitle(g)}</span>
        <Badge tone={state.tone}>{state.text}</Badge>
      </div>
      <ul className="mt-1 space-y-1">
        {g.sources.map((s) => {
          const inUse = g.state === "CHOSEN" && g.chosen_sheet_id === s.sheet_id;
          const here = s.sheet_id === p.currentSheetId;
          return (
            <li key={s.sheet_id} className="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid={`layout-source-${g.key}-${s.page_no}`} data-in-use={inUse}>
              <span className={s.set_aside ? "text-[var(--color-text-muted)] line-through" : ""}>{t("boq.takeoff.layouts.page", "Page {{n}}", { n: s.page_no })}{s.caption ? ` · ${s.caption}` : ""}</span>
              <span className="text-[11.5px] text-[var(--color-text-secondary)]">{sourceLine(s)}</span>
              {g.suggested_sheet_id === s.sheet_id && g.state === "DOUBLE" ? <Badge tone="blue">{t("boq.takeoff.layouts.suggested", "suggested")}</Badge> : null}
              <span className="ml-auto flex items-center gap-1">
                {g.choosable && p.canEdit && !inUse ? (
                  <Button size="sm" disabled={p.busy} onClick={() => p.onChoose({ choices: [{ key: g.key, sheet_id: s.sheet_id }] })} data-testid={`layout-use-${g.key}-${s.page_no}`}>
                    {t("boq.takeoff.layouts.use", "Use page {{n}}", { n: s.page_no })}
                  </Button>
                ) : null}
                {!here ? <Button size="sm" variant="ghost" onClick={() => p.onOpenSheet(s.sheet_id)}>{t("boq.takeoff.layouts.open", "Open")}</Button> : null}
              </span>
            </li>
          );
        })}
      </ul>
      {g.conflict ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-danger)]" data-testid={`layout-conflict-${g.key}`}>
          {t("boq.takeoff.layouts.conflict", "Two of these sheets already have measurements. Delete the measurements of one of them, then choose the other sheet.")}
        </p>
      ) : null}
    </li>
  );
}
