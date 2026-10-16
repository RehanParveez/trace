import { useTranslation } from "react-i18next";
import type { DrawingFacts, FloorCheck } from "../types/takeoff.types";
import { mmText, mmToFeetInches, pagesText } from "../utils/facts";
import { ChecksSection } from "./ChecksSection";
import { StructureSection } from "./StructureSection";
import { FLOOR_STATUS_TONE, OPENING_TYPE_TITLE, SIDE_TEXT, groupOpenings, hasSchedule, lintelText, m2Text, metresText, projectionRows, sizeText, stairText, steelText, suggestedHeightText, wallHeightBasisText } from "../utils/schedule";

interface Props {
  facts: DrawingFacts | undefined;
}

const TONE: Record<string, string> = {
  ok: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  warn: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  muted: "bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]",
};

function FloorRow({ f }: { f: FloorCheck }) {
  const { t } = useTranslation();
  const tone = TONE[FLOOR_STATUS_TONE[f.status]];
  const read = f.status !== "NOT_READ";
  return (
    <div className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid={`floor-check-${f.key}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-[var(--color-text-primary)]">{f.name}</span>
        <span className="text-[var(--color-text-muted)]">{t("drawings.schedule.covered", { defaultValue: "covered {{area}}", area: m2Text(f.covered_m2) })}</span>
        <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${tone}`}>{t(`drawings.schedule.status.${f.status}`, f.status)}</span>
      </div>
      {read ? (
        <ul className="mt-1 list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
          <li>
            {t("drawings.schedule.rooms", { defaultValue: "{{n}} rooms add up to {{area}} ({{pct}}% of covered)", n: f.rooms, area: m2Text(f.rooms_m2), pct: f.coverage_pct ?? 0 })}
          </li>
          <li>
            {t("drawings.schedule.openingsFound", {
              defaultValue: "{{doors}} doors, {{windows}} windows, {{vents}} ventilators · {{area}} of openings",
              doors: f.doors, windows: f.windows, vents: f.ventilators, area: m2Text(f.openings_m2),
            })}
          </li>
          {f.walls_m > 0 ? (
            <li>
              {t("drawings.schedule.wallsFound", { defaultValue: "{{len}} of wall centre line", len: metresText(f.walls_m) })}
              {f.wall_height_mm ? ` · ${t("drawings.schedule.height", { defaultValue: "height {{h}}", h: `${mmToFeetInches(f.wall_height_mm)} (${mmText(f.wall_height_mm)})` })}` : ""}
              {f.wall_height_basis ? ` · ${t(`drawings.schedule.basis.${f.wall_height_basis}`, wallHeightBasisText(f.wall_height_basis))}` : ""}
            </li>
          ) : null}
          {f.brick_9_m2 + f.brick_45_m2 + f.rcc_m2 > 0 ? (
            <li>
              {t("drawings.schedule.netAreas", {
                defaultValue: "net of openings: 9\" brick {{a}} · 4½\" brick {{b}} · concrete wall {{c}}",
                a: m2Text(f.brick_9_m2), b: m2Text(f.brick_45_m2), c: m2Text(f.rcc_m2),
              })}
            </li>
          ) : null}
        </ul>
      ) : null}
      {f.message ? <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{f.message}</p> : null}
    </div>
  );
}

export function DrawingSchedulePanel({ facts }: Props) {
  const { t } = useTranslation();
  if (!facts || !hasSchedule(facts)) return null;
  const groups = groupOpenings(facts);
  const floors = facts.floors ?? [];
  const conflicts = facts.schedule?.conflicts ?? [];
  const heightText = suggestedHeightText(facts);
  const suggest = facts.suggest?.wall_height;
  const fromSection = Object.values(facts.suggest?.wall_height_by_floor ?? {}).some((h) => h.basis === "SECTION");
  const areas = (facts.schedule?.areas ?? []).filter((a) => a.kind !== "FLOOR");
  const lintels = facts.schedule?.lintels ?? [];
  const tieBand = facts.schedule?.tie_band ?? null;
  const stair = facts.schedule?.stair ?? null;
  const projections = projectionRows(facts);
  return (
    <details className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-2.5" data-testid="drawing-schedule">
      <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-text-primary)]">
        {t("drawings.schedule.title", "Schedules and floor checks")}
        {conflicts.length > 0 ? <span className="ml-2 text-[var(--color-danger)]">{t("drawings.facts.conflictCount", { defaultValue: "{{n}} to settle", n: conflicts.length })}</span> : null}
      </summary>
      <div className="mt-2 space-y-2 text-[11.5px]">
        <p className="text-[11px] leading-snug text-[var(--color-text-muted)]">
          {t("drawings.schedule.intro", "Sizes are read from the door and window schedule and the area table printed on the drawing. They are used to deduct openings from each wall. The floor checks set what Trace found beside what the area table says, so a missing room shows up here.")}
        </p>
        {conflicts.map((c) => (
          <div key={`${c.kind}-${c.name}`} className="rounded-[6px] bg-[var(--color-danger-bg)] p-2 text-[var(--color-danger)]" data-testid={`schedule-conflict-${c.name}`}>
            <div className="font-semibold">
              {c.kind === "OPENING_SIZE"
                ? t("drawings.schedule.sizeConflict", { defaultValue: "{{name}} is given two sizes. Trace uses the more common one; check it.", name: c.name })
                : c.kind === "LINTEL_SIZE"
                  ? t("drawings.schedule.lintelConflict", { defaultValue: "The lintel table gives two sections for a span {{name}}. Trace uses the more common one; check it.", name: c.name })
                  : c.kind.startsWith("STAIR_")
                    ? t("drawings.schedule.stairConflict", { defaultValue: "The drawing gives two values for the stair {{name}}. Trace uses the more common one; check it.", name: c.name })
                    : t("drawings.schedule.areaConflict", { defaultValue: "{{name}} has two areas. Trace uses the more common one; check it.", name: c.name })}
            </div>
            <ul className="mt-1 list-none space-y-0.5 pl-0">
              {c.values.map((v) => (
                <li key={`${v.width_mm ?? ""}-${v.height_mm ?? ""}-${v.m2 ?? ""}-${v.value ?? ""}`}>
                  {v.width_mm != null && v.height_mm != null ? sizeText(v.width_mm, v.height_mm) : v.width_mm != null && v.depth_mm != null ? lintelText(v.width_mm, v.depth_mm) : v.m2 != null ? m2Text(v.m2) : v.value != null ? String(v.value) : ""} · {t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText(v.pages) })}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {suggest && heightText && !fromSection ? (
          <div className="rounded-[6px] border border-[var(--color-border)] p-2" data-testid="suggested-wall-height">
            <span className="font-semibold text-[var(--color-text-primary)]">{t("drawings.schedule.suggestedHeight", "Wall height to confirm")}</span>{" "}
            {heightText}{" "}
            <span className="text-[var(--color-text-muted)]">
              {t("drawings.schedule.suggestedHeightHint", {
                defaultValue: "floor to floor {{f2f}} less slab {{slab}}. Trace has not applied this; set it on the wall when you agree.",
                f2f: mmToFeetInches(suggest.floor_to_floor_mm), slab: mmToFeetInches(suggest.slab_mm),
              })}
            </span>
            {suggest.alternatives.length > 0 ? (
              <div className="mt-0.5 text-[var(--color-text-muted)]">
                {t("drawings.schedule.otherSlabs", "Another slab is printed too:")}{" "}
                {suggest.alternatives.map((a) => `${mmToFeetInches(a.slab_mm)} → ${mmToFeetInches(a.value_mm)}`).join(", ")}
              </div>
            ) : null}
          </div>
        ) : null}
        {floors.length > 0 ? (
          <div className="space-y-1.5" data-testid="floor-checks">
            <div className="font-semibold text-[var(--color-text-primary)]">{t("drawings.schedule.floors", "Floor by floor")}</div>
            {floors.map((f) => <FloorRow key={f.key} f={f} />)}
           </div>
        ) : null}
        {projections.length > 0 ? (
          <div data-testid="schedule-projections">
            <div className="font-semibold text-[var(--color-text-primary)]">{t("drawings.schedule.projections", "Roof projections")}</div>
            <p className="text-[11px] leading-snug text-[var(--color-text-muted)]">{t("drawings.schedule.projectionsHint", "The slab reaches past the walls by these widths. They are added to the covered area of the floor when its slab is found. Which side a label belongs to is read from where it sits on the plan.")}</p>
            <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
              {projections.map((r) => (
                <li key={r.floor} data-testid={`projection-${r.floor}`}>
                  <span className="font-semibold text-[var(--color-text-primary)]">{r.name}</span>
                  {r.sides.map((s) => ` · ${t(`drawings.schedule.side.${s.side}`, SIDE_TEXT[s.side] ?? s.side)} ${mmToFeetInches(s.widthMm)}`).join("")}
                  {r.sides.length > 0 ? ` · ${t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText([...new Set(r.sides.flatMap((s) => s.pages))].sort((a, b) => a - b)) })}` : ""}
                  {r.conflicts.map((c) => (
                    <div key={c.side} className="text-[var(--color-danger)]">{t("drawings.schedule.projectionConflict", { defaultValue: "{{side}} is printed with different widths ({{widths}}). It is not added.", side: t(`drawings.schedule.side.${c.side}`, SIDE_TEXT[c.side] ?? c.side), widths: c.widthsMm.map((w) => mmToFeetInches(w)).join(", ") })}</div>
                  ))}
                  {r.unplaced.map((u) => (
                    <div key={u} className="text-[var(--color-warning)]">{t("drawings.schedule.projectionUnplaced", { defaultValue: "A label could not be placed on a side: {{text}}. It is not added.", text: u })}</div>
                  ))}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <StructureSection facts={facts} />
        <ChecksSection facts={facts} />
        {groups.map((g) => (
          <div key={g.type} data-testid={`schedule-${g.type}`}>
            <div className="font-semibold text-[var(--color-text-primary)]">{t(`drawings.schedule.type.${g.type}`, OPENING_TYPE_TITLE[g.type] ?? g.type)}</div>
            <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
              {g.rows.map((r) => (
                <li key={`${g.type}-${r.mark}`}>
                  <span className="font-semibold text-[var(--color-text-primary)]">{r.mark}</span> · {sizeText(r.width_mm, r.height_mm)} · {t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText(r.pages) })}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {lintels.length > 0 ? (
          <div data-testid="schedule-lintels">
            <div className="font-semibold text-[var(--color-text-primary)]">{t("drawings.schedule.lintels", "Lintel table")}</div>
            <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
              {lintels.map((r) => (
                <li key={r.span_max_ft}>
                  {t("drawings.schedule.lintelRow", { defaultValue: "span up to {{ft}} ft", ft: r.span_max_ft })} · <span className="font-semibold text-[var(--color-text-primary)]">{lintelText(r.width_mm, r.depth_mm)}</span>{r.steel ? <> · <span data-testid="lintel-steel">{steelText(r.steel)}</span></> : null} · {t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText(r.pages) })}
                </li>
              ))}
            </ul>
            {tieBand ? <div className="mt-0.5 text-[var(--color-text-muted)]" data-testid="schedule-tie-band">{t("drawings.schedule.tieBand", { defaultValue: "A tie band is printed too ({{text}}). It is not measured; see the checks.", text: tieBand.text.toLowerCase() })}</div> : null}
          </div>
        ) : null}
        {stair ? (
          <div data-testid="schedule-stair">
            <div className="font-semibold text-[var(--color-text-primary)]">{t("drawings.schedule.stair", "Staircase")}</div>
            <div className="text-[var(--color-text-muted)]">
              {stairText(stair)} · {t("drawings.facts.onSheets", { defaultValue: "sheet {{pages}}", pages: pagesText(stair.pages) })}
            </div>
            {!stair.waist_mm ? <div className="mt-0.5 text-[var(--color-text-muted)]">{t("drawings.schedule.stairWaist", "The waist slab under the steps is not printed. 5 inches is assumed when the stair is listed.")}</div> : null}
          </div>
        ) : null}
        {areas.length > 0 ? (
          <div>
            <div className="font-semibold text-[var(--color-text-primary)]">{t("drawings.schedule.otherAreas", "Other areas on the table")}</div>
            <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
              {areas.map((a) => <li key={a.key}>{a.name} · {m2Text(a.m2)}</li>)}
            </ul>
          </div>
        ) : null}
      </div>
    </details>
  );
}
