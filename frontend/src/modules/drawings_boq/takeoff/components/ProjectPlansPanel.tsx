import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import { useChooseFloorSources, useTakeoffFloorSources } from "../hooks/useTakeoff";
import { planFloors, planSummary } from "../utils/projectFacts";

interface Props {
  drawingId: string | undefined;
  canEdit: boolean;
  drawings: number;
}

export function ProjectPlansPanel(p: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const sources = useTakeoffFloorSources(p.drawingId, p.drawings > 1);
  const choose = useChooseFloorSources(p.drawingId);
  if (p.drawings < 2) return null;
  const floors = planFloors(sources.data);
  if (!floors.length) return null;
  const count = sources.data?.drawings ?? p.drawings;
  return (
    <section className="border-b border-[var(--color-border)] px-4 py-2 text-[12px]" data-testid="project-plans" data-floors={floors.length}>
      <button type="button" className="flex w-full items-center gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open} data-testid="project-plans-toggle">
        <span className="font-semibold">{t("boq.takeoff.projectPlans.title", "Plans of each floor, from all PDFs")}</span>
        <span className="text-[11.5px] text-[var(--color-text-secondary)]">{planSummary(floors, count)}</span>
        <span className="ml-auto text-[11.5px] text-[var(--color-text-secondary)]">{open ? t("boq.takeoff.projectPlans.hide", "Hide") : t("boq.takeoff.projectPlans.show", "Show")}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-2">
          <p className="text-[11.5px] text-[var(--color-text-secondary)]">
            {t("boq.takeoff.projectPlans.help", "When a floor is drawn on more than one plan, one plan is its base plan and the others are not counted again: a working drawing with dimensions comes first, then the furniture layout. Services overlays, framing plans and foundation plans are never the base plan and are never set aside. If the wrong plan was chosen, use Make base plan on the right one.")}
          </p>
          {choose.error ? <p className="text-[11.5px] text-[var(--color-danger)]" data-testid="project-plans-error">{t("boq.takeoff.projectPlans.failed", "The base plan could not be changed. Try again.")}</p> : null}
          {floors.map((f) => (
            <div key={f.floor} className="rounded-[8px] border border-[var(--color-border)] px-2 py-1" data-testid={`project-plans-${f.floor}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{f.floorText}</span>
                {f.reason ? <span className="text-[11.5px] text-[var(--color-text-secondary)]">{f.reason}</span> : null}
              </div>
              <ul className="mt-1 space-y-1">
                {f.plans.map((r) => (
                  <li key={r.sheetId} className="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid={`project-plan-${r.pageNo}`} data-base={r.base ? "1" : "0"} data-taking={r.taking ? "1" : "0"}>
                    <span className="font-semibold">{t("boq.takeoff.roles.page", "Page {{n}}", { n: r.pageNo })}</span>
                    {r.drawingName ? <Badge tone="slate">{r.drawingName}</Badge> : null}
                    <Badge tone="slate">{r.kindText}</Badge>
                    {r.dims > 0 ? <span className="text-[11.5px] text-[var(--color-text-secondary)]">{t("boq.takeoff.projectPlans.dims", "{{n}} dimension strings", { n: r.dims })}</span> : null}
                    {r.base ? <Badge tone="green">{t("boq.takeoff.projectPlans.base", "base plan")}</Badge> : null}
                    {!r.taking ? <Badge tone="blue">{t("boq.takeoff.projectPlans.notInChoice", "not an alternative")}</Badge> : null}
                    {r.taking && !r.base && r.setAside ? <Badge tone="gold">{t("boq.takeoff.projectPlans.setAside", "set aside")}</Badge> : null}
                    {r.taking && !r.base && f.choosable && p.canEdit ? (
                      <Button size="sm" className="ml-auto" disabled={choose.isPending} onClick={() => choose.mutate({ choices: [{ floor: f.floor, sheet_id: r.sheetId }] })} data-testid={`project-plan-make-base-${r.pageNo}`}>
                        {t("boq.takeoff.projectPlans.makeBase", "Make base plan")}
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
