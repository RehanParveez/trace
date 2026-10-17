import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../organizations/components/OrganizationUi";
import type { DatumView } from "../api/datums.api";
import type { ElementParameterRange } from "../api/elementParams.api";
import type { RunStats } from "../types/drawings-boq.types";
import { ELEMENT_NAMES, balanceView, bandText, dpcView, elementRows, missingTypedNames, parseElementValue, parseLevel } from "../utils/levels";
import type { ElementRow } from "../utils/levels";
import { useStageLabel } from "./StageBadge";

const BOX =
  "w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 font-mono text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]";
const HEAD = "text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]";

const BASIS_TEXT: Record<string, string> = {
  model: "From the model",
  drawing: "From the drawing",
  param: "Your setting",
  user: "Your setting",
  default: "Assumed",
  typed: "Typed by you",
  convention: "Convention",
  element: "Set for this footing",
  claim: "Read from the drawing",
};

const DPC_WHY_TEXT: Record<string, string> = {
  ALL_ITEMS_IN_MODEL: "The model already carries a damp-proof course item, so none was added.",
  NO_PROFILE: "No DPC was measured because the work item list was not ready.",
  NO_WALL_ON_DPC: "No DPC was measured: no wall stands across the DPC level.",
  NO_DPC_LEVEL: "No DPC was measured: no DPC level could be found. Type one under Reference levels.",
};

function basisTone(basis: string | null | undefined): "green" | "blue" | "gold" | "slate" {
  if (basis === "model" || basis === "drawing") return "green";
  if (basis === "typed" || basis === "param" || basis === "user" || basis === "element") return "blue";
  if (basis === "default") return "gold";
  return "slate";
}

export function BasisBadge({ basis }: { basis: string | null | undefined }) {
  const { t } = useTranslation();
  if (!basis) return null;
  return (
    <span data-testid={`basis-${basis}`}>
      <Badge tone={basisTone(basis)}>{t(`boq.levels.basis.${basis}`, BASIS_TEXT[basis] ?? basis)}</Badge>
    </span>
  );
}

function Block({ title, hint, testId, children }: { title: string; hint?: string; testId: string; children: React.ReactNode }) {
  return (
    <section data-testid={testId} className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{title}</div>
      {hint ? <p className="mt-1 text-[11px] leading-snug text-[var(--color-text-muted)]">{hint}</p> : null}
      <div className="mt-2">{children}</div>
    </section>
  );
}

export interface DatumEditorProps {
  datums: readonly DatumView[];
  typed: Record<string, number>;
  draft: Record<string, string>;
  onDraft: (next: Record<string, string>) => void;
  onSave: () => void;
  saving: boolean;
  canEdit: boolean;
}

export function DatumEditor({ datums, typed, draft, onDraft, onSave, saving, canEdit }: DatumEditorProps) {
  const { t } = useTranslation();
  const orphans = missingTypedNames(typed, datums);
  const rows = [...datums];
  for (const name of orphans) {
    rows.push({ name, label: name, typed_z_mm: typed[name], run_z_mm: null, run_basis: null, run_note: null, editable: true });
  }
  const bad = rows.some((d) => d.editable && parseLevel(draft[d.name]).error);
  return (
    <Block
      testId="datum-editor"
      title={t("boq.levels.datumsTitle", "Reference levels")}
      hint={t(
        "boq.levels.datumsHint",
        "The levels the run cut the building at. Type a level in millimetres to use it in place of the one found, and run again. A level left empty is found from the model or the drawing, and one found that way from nothing is marked assumed.",
      )}
    >
      {rows.length === 0 ? (
        <p data-testid="datum-empty" className="text-[12px] text-[var(--color-text-secondary)]">
          {t("boq.levels.noDatums", "No run has recorded levels yet. Run the calculation with stages on, then the levels appear here.")}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[12px]">
            <thead>
              <tr>
                <th className={`${HEAD} py-1 pr-3`}>{t("boq.levels.col.level", "Level")}</th>
                <th className={`${HEAD} py-1 pr-3`}>{t("boq.levels.col.run", "Last run (mm)")}</th>
                <th className={`${HEAD} py-1 pr-3`}>{t("boq.levels.col.basis", "How found")}</th>
                <th className={`${HEAD} py-1`}>{t("boq.levels.col.typed", "Use this level (mm)")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const parsed = parseLevel(draft[d.name]);
                return (
                  <tr key={d.name} data-testid={`datum-${d.name}`} className="border-t border-[var(--color-border)] align-top">
                    <td className="py-1.5 pr-3">
                      <div className="font-mono text-[12px] font-semibold text-[var(--color-text-primary)]">{d.name}</div>
                      <div className="text-[11px] text-[var(--color-text-muted)]">{d.label}</div>
                    </td>
                    <td className="py-1.5 pr-3 font-mono">{d.run_z_mm === null ? "-" : d.run_z_mm}</td>
                    <td className="py-1.5 pr-3">
                      <BasisBadge basis={d.run_basis} />
                      {d.run_note ? <div className="mt-1 max-w-[260px] text-[11px] text-[var(--color-text-muted)]">{d.run_note}</div> : null}
                    </td>
                    <td className="py-1.5">
                      {d.editable ? (
                        <>
                          <input
                            data-testid={`datum-input-${d.name}`}
                            className={BOX}
                            inputMode="decimal"
                            value={draft[d.name] ?? ""}
                            disabled={!canEdit}
                            placeholder={d.run_basis && d.run_basis !== "typed" ? t("boq.levels.found", "found by the run") : ""}
                            onChange={(event) => onDraft({ ...draft, [d.name]: event.target.value })}
                          />
                          {parsed.error ? (
                            <span className="mt-1 block text-[11px] text-[var(--color-danger)]">
                              {parsed.error === "NOT_A_NUMBER"
                                ? t("boq.derived.error.NOT_A_NUMBER", "Enter a number")
                                : t("boq.levels.error.range", "Enter a level from -100000 to 300000 mm")}
                            </span>
                          ) : null}
                        </>
                      ) : (
                        <span className="text-[11px] text-[var(--color-text-muted)]">{t("boq.levels.notTyped", "Shown only")}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {rows.some((d) => d.editable) ? (
        <div className="mt-3">
          <Button variant="primary" size="sm" data-testid="datum-save" disabled={!canEdit || saving || bad} onClick={onSave}>
            {saving ? t("boq.levels.saving", "Saving") : t("boq.levels.save", "Save levels")}
          </Button>
        </div>
      ) : null}
    </Block>
  );
}

export function BandsList({ stats }: { stats?: RunStats }) {
  const { t } = useTranslation();
  const stageLabel = useStageLabel();
  const bands = stats?.stages?.bands ?? [];
  const unused = stats?.stages?.unused_overrides ?? [];
  if (bands.length === 0 && unused.length === 0) return null;
  return (
    <Block
      testId="stage-bands"
      title={t("boq.levels.bandsTitle", "Stages of the building")}
      hint={t("boq.levels.bandsHint", "Each stage runs between two levels. A stage marked assumed has a level that was not read from the building.")}
    >
      <ul className="space-y-1">
        {bands.map((b) => (
          <li key={b.stage} data-testid={`band-${b.stage}`} className="flex flex-wrap items-center gap-2 text-[12px]">
            <span className="min-w-[150px] font-semibold text-[var(--color-text-primary)]">{stageLabel(b.stage)}</span>
            <span className="font-mono text-[var(--color-text-secondary)]">{bandText(b)}</span>
            {stats?.stages?.rows_by_stage?.[b.stage] !== undefined ? (
              <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
                {t("boq.levels.rows", { defaultValue: "{{n}} rows", n: stats.stages.rows_by_stage[b.stage] })}
              </span>
            ) : null}
            {b.defaulted ? <Badge tone="gold">{t("boq.levels.basis.default", "Assumed")}</Badge> : null}
            {b.soft ? <Badge tone="slate">{t("boq.levels.soft", "By height only")}</Badge> : null}
          </li>
        ))}
      </ul>
      {unused.length > 0 ? (
        <p data-testid="unused-overrides" className="mt-2 text-[12px] text-[var(--color-warning)]">
          {t("boq.levels.unused", {
            defaultValue: "A level you typed was not used: {{names}}. The building has no such level, or it falls outside the others.",
            names: unused.join(", "),
          })}
        </p>
      ) : null}
    </Block>
  );
}

export function BalanceBlock({ stats }: { stats?: RunStats }) {
  const { t } = useTranslation();
  const v = balanceView(stats?.derived?.balance);
  if (!v) return null;
  const cells: Array<[string, string, string]> = [
    ["excavation", t("boq.levels.balance.excavation", "Dug"), v.excavation],
    ["backfill", t("boq.levels.balance.backfill", "Filled back"), v.backfill],
    ["buried", t("boq.levels.balance.buried", "Taken by the work in the trench"), v.buried],
    ["carted", t("boq.levels.balance.carted", "Earth to cart away"), v.carted],
  ];
  return (
    <Block
      testId="earth-balance"
      title={t("boq.levels.balanceTitle", "Earth balance")}
      hint={t("boq.levels.balanceHint", "What was dug equals what goes back plus what the permanent work takes. The three must close.")}
    >
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {cells.map(([key, label, value]) => (
          <div key={key} data-testid={`balance-${key}`}>
            <div className={HEAD}>{label}</div>
            <div className="mt-1 font-mono text-[14px] font-semibold text-[var(--color-text-primary)]">{value} m3</div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
        {v.closes ? (
          <span data-testid="balance-closes"><Badge tone="green">{t("boq.levels.balance.closes", "Closes")}</Badge></span>
        ) : (
          <span data-testid="balance-open">
            <Badge tone="red">{t("boq.levels.balance.open", { defaultValue: "Does not close: gap {{gap}} m3", gap: v.gap })}</Badge>
          </span>
        )}
        {v.negativeRows > 0 ? (
          <span data-testid="balance-negative">
            <Badge tone="red">{t("boq.levels.balance.negative", { defaultValue: "{{n}} backfill rows came out below zero", n: v.negativeRows })}</Badge>
          </span>
        ) : null}
        {v.outsideTaken ? (
          <span data-testid="balance-outside">
            <Badge tone="gold">
              {t("boq.levels.balance.outside", {
                defaultValue: "{{m3}} m3 of structure sits below ground outside any trench",
                m3: v.outside,
              })}
            </Badge>
          </span>
        ) : null}
      </div>
    </Block>
  );
}

export function DpcBlock({ stats }: { stats?: RunStats }) {
  const { t } = useTranslation();
  const v = dpcView(stats);
  if (!v) return null;
  const assumed = stats?.derived?.dpc?.params;
  return (
    <Block
      testId="dpc-summary"
      title={t("boq.levels.dpcTitle", "Damp-proof course")}
      hint={t("boq.levels.dpcHint", "Measured as an area on every wall that stands across the DPC level. Walls that stand on the DPC are counted once, doors are taken out when the door deduction is on.")}
    >
      {v.ran ? (
        <div className="flex flex-wrap items-center gap-3 text-[12px]">
          <span data-testid="dpc-area" className="font-mono text-[14px] font-semibold text-[var(--color-text-primary)]">{v.areaM2} m2</span>
          <span className="text-[var(--color-text-secondary)]">{t("boq.levels.dpcRows", { defaultValue: "{{n}} rows", n: v.rows })}</span>
          <span className="text-[var(--color-text-secondary)]">
            {t("boq.levels.dpcDoors", { defaultValue: "{{n}} doors taken out", n: v.doorsTakenOut })}
          </span>
          {v.levelMm !== null ? <span className="font-mono text-[var(--color-text-secondary)]">{v.levelMm} mm</span> : null}
          <BasisBadge basis={v.levelSource} />
        </div>
      ) : (
        <p data-testid="dpc-not-measured" className="text-[12px] text-[var(--color-text-secondary)]">
          {t(`boq.levels.dpcWhy.${v.why ?? "NO_WALL_ON_DPC"}`, DPC_WHY_TEXT[v.why ?? "NO_WALL_ON_DPC"])}
        </p>
      )}
      {assumed ? (
        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-[var(--color-text-secondary)]">
          {Object.entries(assumed).map(([name, p]) => (
            <span key={name} data-testid={`dpc-param-${name}`} className="flex items-center gap-1">
              {t(`boq.derived.param.${name}`, name)}: <span className="font-mono">{p.value}</span>
              <BasisBadge basis={p.source} />
            </span>
          ))}
        </div>
      ) : null}
      {!v.verticalTaken ? (
        <p data-testid="dpc-vertical" className="mt-2 text-[11px] text-[var(--color-text-muted)]">
          {t("boq.levels.dpcVertical", "The vertical DPC, up the face of a wall, is not taken. Add it by hand if the specification asks for it.")}
        </p>
      ) : null}
    </Block>
  );
}

export interface ElementEditorProps {
  stats?: RunStats;
  labels: Record<string, string>;
  ranges: Record<string, ElementParameterRange>;
  draft: Record<string, Record<string, string>>;
  onDraft: (next: Record<string, Record<string, string>>) => void;
  onSave: () => void;
  saving: boolean;
  canEdit: boolean;
}

export function ElementEditor({ stats, labels, ranges, draft, onDraft, onSave, saving, canEdit }: ElementEditorProps) {
  const { t } = useTranslation();
  const rows: ElementRow[] = elementRows(stats?.derived?.foundation_list, labels);
  const unmatched = stats?.derived?.element_overrides?.unmatched ?? [];
  if (rows.length === 0 && unmatched.length === 0) return null;
  const bad = rows.some((r) => r.names.some((n) => parseElementValue(draft[r.id]?.[n], ranges[n]).error));
  return (
    <Block
      testId="element-editor"
      title={t("boq.levels.elementsTitle", "Values for one footing")}
      hint={t(
        "boq.levels.elementsHint",
        "The project values hold for every footing. Type a value here to change it for that footing alone; its rows are then marked as set for the element. Leave a box empty to use the project value.",
      )}
    >
      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[12px]">
            <thead>
              <tr>
                <th className={`${HEAD} py-1 pr-3`}>{t("boq.levels.col.element", "Footing")}</th>
                {ELEMENT_NAMES.map((n) => (
                  <th key={n} className={`${HEAD} py-1 pr-3`}>{t(`boq.derived.param.${n}`, n)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-testid={`element-${r.id}`} className="border-t border-[var(--color-border)] align-top">
                  <td className="py-1.5 pr-3">
                    <div className="font-semibold text-[var(--color-text-primary)]">{r.label}</div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">{r.bed}</div>
                  </td>
                  {ELEMENT_NAMES.map((n) => {
                    const cell = r.values[n];
                    if (!cell) return <td key={n} className="py-1.5 pr-3 text-[var(--color-text-muted)]">-</td>;
                    const parsed = parseElementValue(draft[r.id]?.[n], ranges[n]);
                    return (
                      <td key={n} className="py-1.5 pr-3">
                        <input
                          data-testid={`element-input-${r.id}-${n}`}
                          className={BOX}
                          inputMode="decimal"
                          value={draft[r.id]?.[n] ?? ""}
                          disabled={!canEdit}
                          placeholder={String(cell.value)}
                          onChange={(event) => onDraft({ ...draft, [r.id]: { ...(draft[r.id] ?? {}), [n]: event.target.value } })}
                        />
                        <div className="mt-1"><BasisBadge basis={cell.source} /></div>
                        {parsed.error ? (
                          <span className="block text-[11px] text-[var(--color-danger)]">
                            {t("boq.derived.error.OUT_OF_RANGE", {
                              defaultValue: "Enter a value from {{min}} to {{max}}",
                              min: ranges[n]?.low ?? 0,
                              max: ranges[n]?.high ?? "",
                            })}
                          </span>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {unmatched.length > 0 ? (
        <p data-testid="element-unmatched" className="mt-2 text-[12px] text-[var(--color-warning)]">
          {t("boq.levels.elementsUnmatched", {
            defaultValue: "{{n}} saved footing values match no footing in this run and were not used.",
            n: unmatched.length,
          })}
        </p>
      ) : null}
      {rows.length > 0 ? (
        <div className="mt-3">
          <Button variant="primary" size="sm" data-testid="element-save" disabled={!canEdit || saving || bad} onClick={onSave}>
            {saving ? t("boq.levels.saving", "Saving") : t("boq.levels.saveElements", "Save footing values")}
          </Button>
        </div>
      ) : null}
    </Block>
  );
}
