import { useTranslation } from "react-i18next";
import { Badge, Button, ErrorState } from "../../../organizations/components/OrganizationUi";
import type { FloorChoiceBody, FloorEntry, FloorSources } from "../types/takeoff.types";
import { floorName, floorsToShow, floorState, sourceLine, sourceName, wallGap } from "../utils/floorSources";

interface Props {
  data: FloorSources | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  canEdit: boolean;
  busy: boolean;
  currentSheetId: string;
  planFloors: string[];
  sheetHasPlans: boolean;
  showPlans: boolean;
  onShowPlans: (on: boolean) => void;
  onChoose: (body: FloorChoiceBody) => void;
  onOpenSheet: (sheetId: string) => void;
  onShowPlan: (floor: string) => void;
}

export function FloorSourcesPanel(p: Props) {
  const { t } = useTranslation();
  if (p.loading && !p.data) return <div className="border-b border-[var(--color-border)] p-3 text-[12px] text-[var(--color-text-muted)]" data-testid="floor-sources-loading">{t("boq.takeoff.floorSources.loading", "Checking which floors were read twice…")}</div>;
  if (p.error && !p.data) return <ErrorState title={t("boq.takeoff.floorSources.error", "Couldn't list the floors")} onRetry={p.onRetry} />;
  const floors = floorsToShow(p.data?.floors);
  const repeated = floors.some((f) => f.sources.length > 1);
  if (!repeated && !p.sheetHasPlans) return null;
  const toDecide = p.data?.to_decide ?? 0;
  return (
    <section className="space-y-2 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="floor-sources" data-to-decide={toDecide}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.floorSources.title", "Floors read from this drawing")}</h3>
        {toDecide > 0 ? <Badge tone="gold">{t("boq.takeoff.floorSources.toDecide", "{{n}} to decide", { n: toDecide })}</Badge> : repeated ? <Badge tone="green">{t("boq.takeoff.floorSources.decided", "all decided")}</Badge> : null}
      </div>
      {toDecide > 0 ? (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]">
          {t("boq.takeoff.floorSources.help", "These floors are drawn on more than one sheet and were read from each. Choose the sheet to use for each floor; the other is set aside, so the floor is not counted twice. You can change your mind: the items come back.")}
        </p>
      ) : null}
      {toDecide === 0 && repeated ? (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="floor-sources-auto">
           {floors.some((f) => f.state === "COMBINED")
            ? t("boq.takeoff.floorSources.autoCombined", "A floor drawn on its own sheet and again among the plans was laid over itself by its marks and positions: items both sheets show are counted once and items only one of them shows are kept. To use one sheet only, press its “Use page” button; nothing is deleted.")
            : t("boq.takeoff.floorSources.auto", "A floor drawn on its own sheet and again among the plans is counted once: the floor's own sheet is used and the other is set aside. To use the other sheet instead, press its “Use page” button; nothing is deleted.")}
        </p>
      ) : null}
      {p.sheetHasPlans ? (
        <label className="flex items-center gap-2 text-[11.5px]">
          <input type="checkbox" checked={p.showPlans} onChange={(e) => p.onShowPlans(e.target.checked)} data-testid="floor-sources-show-plans" />
          {t("boq.takeoff.floorSources.showPlans", "Show on the sheet what was read (green) and what was left out (grey)")}
        </label>
      ) : null}
      {toDecide > 0 && p.canEdit ? (
        <Button size="sm" variant="primary" disabled={p.busy} onClick={() => p.onChoose({ use_suggested: true })} data-testid="floor-sources-suggested">
          {toDecide === 1 ? t("boq.takeoff.floorSources.useSuggestedOne", "Use the suggested sheet") : t("boq.takeoff.floorSources.useSuggested", "Use the suggested sheet for all {{n}} floors", { n: toDecide })}
        </Button>
      ) : null}
      <ul className="space-y-2">
        {floors.map((f) => <FloorRow key={f.floor} f={f} p={p} />)}
      </ul>
    </section>
  );
}

function FloorRow({ f, p }: { f: FloorEntry; p: Props }) {
  const { t } = useTranslation();
  const state = f.state === "COMBINED" ? { tone: "green" as const, text: t("takeoff.floorState.COMBINED", "combined") } : floorState(f);
  const gap = f.sources.length > 1 ? wallGap(f) : "";
  return (
    <li className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`floor-source-${f.floor}`} data-state={f.state}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{floorName(f.floor)}</span>
        <Badge tone={state.tone}>{state.text}</Badge>
      </div>
      <ul className="mt-1 space-y-1">
        {f.sources.map((s) => {
          const inUse = f.state === "CHOSEN" && f.chosen_sheet_id === s.sheet_id;
          const here = s.sheet_id === p.currentSheetId;
          return (
            <li key={s.sheet_id} className="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid={`floor-source-${f.floor}-${s.page_no}`} data-in-use={inUse}>
              <span className={s.set_aside ? "text-[var(--color-text-muted)] line-through" : ""}>{sourceName(s)}</span>
              <span className="text-[11.5px] text-[var(--color-text-secondary)]">{sourceLine(s)}</span>
              {s.purpose === "FURNITURE" ? <Badge tone="slate">{t("boq.takeoff.floorSources.furniture", "furniture layout")}</Badge> : null}
              {s.advice === "ASK" ? <Badge tone="gold">{t("boq.takeoff.floorSources.notClearlyPlan", "not clearly a plan")}</Badge> : null}
              {f.state === "COMBINED" && ((s.combined ?? 0) > 0 || (s.added ?? 0) > 0) ? (
                <span className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid={`floor-merge-${f.floor}-${s.page_no}`}>
                  {t("boq.takeoff.floorSources.merge", "{{m}} repeated set aside · {{a}} only on this sheet kept", { m: s.combined ?? 0, a: s.added ?? 0 })}
                </span>
              ) : null}
              {f.suggested_sheet_id === s.sheet_id && f.state === "DOUBLE" ? <Badge tone="blue">{t("boq.takeoff.floorSources.suggested", "suggested")}</Badge> : null}
              <span className="ml-auto flex items-center gap-1">
                {f.choosable && p.canEdit && !inUse ? (
                  <Button size="sm" disabled={p.busy} onClick={() => p.onChoose({ choices: [{ floor: f.floor, sheet_id: s.sheet_id }] })} data-testid={`floor-use-${f.floor}-${s.page_no}`}>
                    {t("boq.takeoff.floorSources.use", "Use page {{n}}", { n: s.page_no })}
                  </Button>
                ) : null}
                {!here ? (
                  <Button size="sm" variant="ghost" onClick={() => p.onOpenSheet(s.sheet_id)} data-testid={`floor-open-${f.floor}-${s.page_no}`}>{t("boq.takeoff.floorSources.open", "Open")}</Button>
                ) : p.planFloors.includes(f.floor) ? (
                  <Button size="sm" variant="ghost" onClick={() => p.onShowPlan(f.floor)} data-testid={`floor-show-${f.floor}`}>{t("boq.takeoff.floorSources.show", "Show on sheet")}</Button>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
      {gap ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{gap}</p> : null}
      {f.conflict ? (
        <p className="mt-1 text-[11.5px] text-[var(--color-danger)]" data-testid={`floor-conflict-${f.floor}`}>
          {t("boq.takeoff.floorSources.conflict", "Both sheets have measurements for this floor. Delete the measurements of one of them, then choose the other sheet.")}
        </p>
      ) : null}
    </li>
  );
}
