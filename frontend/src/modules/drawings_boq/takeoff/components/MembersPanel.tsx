import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import type { Member, MembersView } from "../types/members.types";
import { floorName } from "../utils/floorSources";

interface Props {
  data: MembersView | undefined;
  currentSheetId: string;
  onOpenSheet: (sheetId: string) => void;
}

const KIND: Record<string, string> = { COLUMN: "Columns", FOOTING: "Footings", BEAM: "Beams" };
const BASIS: Record<string, string> = { SCHEDULE: "schedule", DETAIL: "detail", PLAN: "plan" };

export function sizeText(mm: number[] | null): string {
  if (!mm || mm.length === 0) return "size not read";
  return mm.map((v) => `${Math.round((v / 25.4) * 10) / 10}"`).join(" × ");
}

export function memberTitle(m: Member): string {
  return `${m.mark ?? "no mark"} · ${m.floor ? floorName(m.floor) : "floor not named"}`;
}

export function MembersPanel({ data, currentSheetId, onOpenSheet }: Props) {
  const { t } = useTranslation();
  const members = data?.members ?? [];
  if (members.length === 0) return null;
  const several = members.filter((m) => new Set(m.sightings.map((s) => `${s.drawing_id}:${s.page_no}`)).size > 1);
  const open = (data?.decisions ?? []).filter((d) => d.open).length;
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="members">
      <summary className="flex cursor-pointer flex-wrap items-center gap-2">
        <span className="font-semibold">{t("boq.takeoff.members.title", "Columns, footings and beams, each once")}</span>
        <Badge tone="slate">{t("boq.takeoff.members.count", "{{n}} members", { n: members.length })}</Badge>
        {several.length > 0 ? <Badge tone="blue">{t("boq.takeoff.members.several", "{{n}} seen on more than one sheet", { n: several.length })}</Badge> : null}
        {open > 0 ? <Badge tone="gold">{t("boq.takeoff.members.toDecide", "{{n}} to decide", { n: open })}</Badge> : null}
      </summary>
      <p className="mt-2 text-[11.5px] text-[var(--color-text-secondary)]">
        {t("boq.takeoff.members.help", "A member is one column, footing or marked beam of a floor, with every sheet it is drawn on. Its size is the best one printed: a schedule, then a detail, then the plan.")}
      </p>
      {(["COLUMN", "FOOTING", "BEAM"] as const).map((kind) => {
        const rows = members.filter((m) => m.kind === kind);
        if (rows.length === 0) return null;
        return (
          <div key={kind} className="mt-2" data-testid={`members-${kind}`}>
            <h4 className="font-semibold">{KIND[kind]} ({rows.length})</h4>
            <ul className="space-y-1">
              {rows.map((m) => (
                <li key={m.id} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`member-${m.id}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{memberTitle(m)}</span>
                    <span className="text-[11.5px] text-[var(--color-text-secondary)]">{sizeText(m.size_mm)}</span>
                    {!m.positioned && m.kind !== "BEAM" ? <Badge tone="slate">{t("boq.takeoff.members.noPlace", "no place in the plan")}</Badge> : null}
                  </div>
                  <ul className="mt-1 space-y-0.5">
                    {m.sightings.map((s, i) => (
                      <li key={`${s.drawing_id}-${s.page_no}-${s.candidate_key}-${i}`} className="flex flex-wrap items-center gap-2" data-testid={`sighting-${m.id}-${s.page_no}`}>
                        <span>{t("boq.takeoff.members.page", "Page {{n}}", { n: s.page_no })} · {BASIS[s.basis] ?? s.basis}</span>
                        {s.sheet_id && s.sheet_id !== currentSheetId ? <Button size="sm" variant="ghost" onClick={() => onOpenSheet(s.sheet_id as string)}>{t("boq.takeoff.members.open", "Open")}</Button> : null}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </details>
  );
}
