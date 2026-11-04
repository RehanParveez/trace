import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { FORMULA_WORDS, SOURCE_OF, figureCards, gap, kg2, openSentence, signed, tonnes } from "../utils/steelFigures";
import type { SteelFigures, SteelFiguresSource } from "../types/steelFigures.types";

const card = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3";
const label = "text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

interface Props {
  data: SteelFigures;
  canEdit: boolean;
  saving?: boolean;
  onChoose?: (source: SteelFiguresSource) => void;
}

export function SteelFiguresView({ data, canEdit, saving, onChoose }: Props) {
  const { t } = useTranslation();
  const cards = figureCards(data);
  const open = openSentence(data);
  const bbs = data.figures.REBAR_BBS_WEIGHT.kg;
  const audited = data.figures.REBAR_BBS_AUDITED.kg;
  const gapKg = gap(bbs, audited);
  return (
    <div className="space-y-3" data-testid="steel-figures">
      <div className="grid gap-3 sm:grid-cols-3">
        {cards.map((c) => (
          <div key={c.formula} className={`${card} ${c.used ? "ring-2 ring-[var(--color-primary)]" : ""}`} data-testid={`steel-figure-${c.formula}`}>
            <div className={label}>{t(`steel.formula.${c.formula}`, c.words)}</div>
            <div className="mt-1 font-mono text-[18px] font-semibold text-[var(--color-text-primary)]">{c.kg === null ? "—" : `${kg2(c.kg)} kg`}</div>
            <div className="font-mono text-[11.5px] text-[var(--color-text-muted)]">{c.kg === null ? (c.note ?? "") : `${tonnes(c.kg)} t`}</div>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              {c.used ? <Badge tone="green">{t("steel.onBoq", "on the bill")}</Badge> : null}
              {canEdit && onChoose && !c.used && c.kg !== null ? (
                <button type="button" className="text-[11.5px] font-semibold text-[var(--color-primary)] underline disabled:opacity-50" disabled={saving} onClick={() => onChoose(SOURCE_OF[c.formula])}>
                  {t("steel.use", "Use this")}
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      {gapKg !== null ? <p className="text-[12px] text-[var(--color-text-secondary)]">{t("steel.gap", "Audited against billed: {{kg}} kg", { kg: signed(gapKg) })}</p> : null}
      <p className="text-[12.5px] text-[var(--color-text-primary)]" data-testid="steel-line-note">
        <span className="font-semibold">{FORMULA_WORDS[data.line.formula ?? "REBAR_BBS_WEIGHT"] ?? ""}</span>
        {data.line.formula ? ": " : ""}{data.line.note}
      </p>
      {open ? <p className="text-[12px] font-semibold text-[var(--color-warning)]" data-testid="steel-open">{open}</p> : null}
      {data.ledger_gap_kg !== null ? <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("steel.ledgerGap", "The run's bar schedule weight differs from the schedule document by {{kg}} kg.", { kg: signed(data.ledger_gap_kg) })}</p> : null}
      {data.by_diameter.length > 0 ? (
        <div className="overflow-x-auto" data-testid="steel-by-diameter">
          <table className="w-full min-w-[460px] text-left">
            <thead><tr>
              <th className={th}>{t("steel.dia", "Bar size")}</th>
              <th className={`${th} text-right`}>{t("steel.billed", "Billed kg")}</th>
              <th className={`${th} text-right`}>{t("steel.applied", "Accepted findings kg")}</th>
              <th className={`${th} text-right`}>{t("steel.audited", "Audited kg")}</th>
            </tr></thead>
            <tbody>
              {data.by_diameter.map((r) => (
                <tr key={r.dia} className="border-t border-[var(--color-border)]">
                  <td className="px-3 py-2 text-[12.5px]">{r.label}{r.mm ? <span className="ml-1 text-[var(--color-text-muted)]">{r.mm} mm</span> : null}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{kg2(r.bbs_kg)}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{signed(r.applied_kg)}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{data.has_audit ? kg2(r.audited_kg) : "—"}</td>
                </tr>
              ))}
              {data.unattributed_kg !== null && Number(data.unattributed_kg) !== 0 ? (
                <tr className="border-t border-[var(--color-border)] text-[var(--color-text-muted)]">
                  <td className="px-3 py-2 text-[12px]" colSpan={3}>{t("steel.loose", "Not tied to one bar size (findings on several sizes, rows with no size)")}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{signed(data.unattributed_kg)}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}
      {data.allocated_kg !== null && Number(data.allocated_kg) !== 0 ? (
        <p className="text-[11.5px] text-[var(--color-text-muted)]" data-testid="steel-allocated">
          {t("steel.allocated", "{{kg}} kg of the accepted findings name rows of several bar sizes; it is shared over those sizes in proportion to their billed weight, so the split by size is an allocation, not a measurement.", { kg: signed(data.allocated_kg) })}
        </p>
      ) : null}
      {data.wastage ? (
        <p className="font-mono text-[12px] text-[var(--color-text-secondary)]" data-testid="steel-wastage">
          {t("steel.wastage", "Wastage {{pct}} %: {{kg}} kg, kept as its own line (total with wastage {{total}} kg)", { pct: data.wastage.pct, kg: kg2(data.wastage.kg), total: kg2(data.wastage.total_kg) })}
        </p>
      ) : null}
    </div>
  );
}
