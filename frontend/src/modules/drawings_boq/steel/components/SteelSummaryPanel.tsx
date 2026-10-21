import { useState } from "react";
import { useTranslation } from "react-i18next";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { allowancesLine } from "../../utils/steelAllowances";
import { useDownloadSteelSummary, useSteelSummary } from "../hooks/useSteelSummary";
import type { SteelFamilyRow } from "../types/steelSummary.types";
import { BASIS_TONE, BASIS_WORDS, STATUS_TONE, STATUS_WORDS, WASTAGE_CHOICES, apiErrorText, asRunText, diaKgOf, diaText, estimateWarning, filterWords, intensityText, kgText, marksFor, parseWastage, rangeText, tonnesText, type MarkFilter } from "../utils/steelSummary";

const TONE: Record<string, string> = {
  ok: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  warn: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  bad: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  muted: "bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]",
};

export function SteelSummaryPanel({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const [wastageText, setWastageText] = useState("");
  const [custom, setCustom] = useState("");
  const [filter, setFilter] = useState<MarkFilter>({});
  const [error, setError] = useState<string | null>(null);
  const chosen = parseWastage(custom.trim() !== "" ? custom : wastageText);
  const wastage = chosen === "wrong" ? null : chosen;
  const query = useSteelSummary(runId, wastage);
  const download = useDownloadSteelSummary();
  const s = query.data;
  const labelOf = (family: string) => s?.by_family.find((f) => f.family === family)?.label ?? family;
  const marks = s ? marksFor(s.marks, filter) : [];
  const toggle = (next: MarkFilter) => setFilter((cur) => ({ family: next.family !== undefined ? (cur.family === next.family ? null : next.family) : cur.family, dia: next.dia !== undefined ? (cur.dia === next.dia ? null : next.dia) : cur.dia }));
  const warning = s ? estimateWarning(s) : "";
  return (
    <div className="space-y-3 px-4 py-3 text-[12.5px]" data-testid="steel-summary-panel">
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("drawings.steelSummary.intro", "All the steel of this run in one place: by bar diameter and by kind of member, with the weight per cubic metre of concrete against the usual range. Press a line to see the marks behind it.")}
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.steelSummary.wastage", "Wastage")}</span>
          <select className="rounded-[6px] border border-[var(--color-border)] px-2 py-1" value={wastageText} onChange={(e) => { setWastageText(e.target.value); setCustom(""); }} data-testid="steel-wastage">
            {WASTAGE_CHOICES.map((c) => <option key={c.value} value={c.value}>{t(`drawings.steelSummary.wastage.${c.value || "run"}`, c.label)}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[var(--color-text-muted)]">{t("drawings.steelSummary.wastageOther", "or another percent (0 to 15)")}</span>
          <input className={`w-20 rounded-[6px] border px-2 py-1 ${chosen === "wrong" ? "border-[var(--color-danger)]" : "border-[var(--color-border)]"}`} inputMode="decimal" value={custom} onChange={(e) => setCustom(e.target.value)} data-testid="steel-wastage-custom" />
        </label>
        <button type="button" disabled={!s || download.isPending} data-testid="steel-export" className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] underline disabled:opacity-50"
          onClick={() => s && download.mutate(s, { onSuccess: (blob) => triggerBlobDownload(blob, "steel-summary.xlsx"), onError: (e) => setError(apiErrorText(e, t("drawings.steelSummary.exportFailed", "The file could not be made."))) })}>
          {t("drawings.steelSummary.export", "Download as Excel")}
        </button>
      </div>
      {chosen === "wrong" ? <p role="alert" className="text-[var(--color-danger)]">{t("drawings.steelSummary.wrongWastage", "Wastage is a number from 0 to 15.")}</p> : null}
      {error ? <p role="alert" className="text-[var(--color-danger)]">{error}</p> : null}
      {query.isError ? <p role="alert" className="text-[var(--color-danger)]">{apiErrorText(query.error, t("drawings.steelSummary.failed", "The steel could not be summed."))}</p> : null}
      {query.isLoading ? <p className="text-[var(--color-text-muted)]">{t("drawings.steelSummary.loading", "Loading...")}</p> : null}
      {s && s.totals.members === 0 ? <p className="text-[var(--color-text-muted)]" data-testid="steel-none">{t("drawings.steelSummary.none", "This run has no steel. Bars come from the drawing's notes, a bar schedule, or an estimate from the size of the members.")}</p> : null}
      {s && s.totals.members > 0 ? (
        <>
          <p data-testid="steel-total" className="text-[14px] font-semibold">
            {kgText(s.totals.kg)} kg <span className="font-normal text-[var(--color-text-muted)]">({tonnesText(s.totals.kg)} t, {s.totals.members} members)</span>
          </p>
          <p className="text-[11.5px] text-[var(--color-text-muted)]">{asRunText(s)}</p>
          {s.allowances ? (
            <p className="text-[11.5px] text-[var(--color-text-muted)]" data-testid="steel-allowances-line">
              {allowancesLine(s.allowances)}
            </p>
          ) : null}
          {warning ? <p className="text-[var(--color-warning)]" data-testid="steel-estimate-warning">{warning}</p> : null}
          <div className="flex flex-wrap gap-2">
            {Object.entries(s.totals.by_basis).map(([b, v]) => (
              <span key={b} className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${TONE[BASIS_TONE[b as keyof typeof BASIS_TONE]]}`}>{BASIS_WORDS[b as keyof typeof BASIS_WORDS]}: {kgText(v?.kg)} kg</span>
            ))}
          </div>

          <table className="w-full text-[12px]" data-testid="steel-by-diameter">
            <caption className="pb-1 text-left font-semibold">{t("drawings.steelSummary.byDiameter", "By bar diameter")}</caption>
            <thead>
              <tr className="text-left text-[var(--color-text-muted)]">
                <th className="font-medium">{t("drawings.steelSummary.diameter", "Diameter")}</th>
                <th className="text-right font-medium">{t("drawings.steelSummary.weight", "Weight (kg)")}</th>
                <th className="text-right font-medium">{t("drawings.steelSummary.length", "Length (m)")}</th>
                <th className="text-right font-medium">{t("drawings.steelSummary.share", "Share")}</th>
                <th className="font-medium">{t("drawings.steelSummary.usedIn", "Used in")}</th>
              </tr>
            </thead>
            <tbody>
              {s.by_diameter.map((d) => (
                <tr key={d.dia_mm} className={`cursor-pointer hover:bg-[var(--color-surface-muted)] ${filter.dia !== null && filter.dia !== undefined && Number(filter.dia) === d.dia_mm ? "bg-[var(--color-surface-muted)]" : ""}`}
                  onClick={() => toggle({ dia: String(d.dia_mm) })} data-testid={`steel-dia-${d.dia_mm}`}>
                  <td>{diaText(d.dia_mm)}</td>
                  <td className="text-right">{kgText(d.kg)}</td>
                  <td className="text-right">{kgText(d.length_m)}</td>
                  <td className="text-right">{d.share_pct.toFixed(1)}%</td>
                  <td className="text-[var(--color-text-muted)]">{Object.entries(d.by_family).map(([f, k]) => `${labelOf(f)} ${kgText(k)}`).join(", ")}</td>
                </tr>
              ))}
              {s.without_diameter.members > 0 ? (
                <tr data-testid="steel-no-dia">
                  <td colSpan={5} className="pt-1 text-[var(--color-text-muted)]">
                    {t("drawings.steelSummary.noDiameter", "{{kg}} kg in {{n}} members has no diameter: it is estimated from the size, so the bars are not known.", { kg: kgText(s.without_diameter.kg), n: s.without_diameter.members })}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>

          <table className="w-full text-[12px]" data-testid="steel-by-family">
            <caption className="pb-1 text-left font-semibold">{t("drawings.steelSummary.byFamily", "By kind of member")}</caption>
            <thead>
              <tr className="text-left text-[var(--color-text-muted)]">
                <th className="font-medium">{t("drawings.steelSummary.kind", "Kind")}</th>
                <th className="text-right font-medium">{t("drawings.steelSummary.members", "Members")}</th>
                <th className="text-right font-medium">{t("drawings.steelSummary.weight", "Weight (kg)")}</th>
                <th className="text-right font-medium">{t("drawings.steelSummary.concrete", "Concrete (m3)")}</th>
                <th className="font-medium">{t("drawings.steelSummary.intensity", "Steel per m3 of concrete")}</th>
              </tr>
            </thead>
            <tbody>
              {s.by_family.map((f: SteelFamilyRow) => (
                <tr key={f.family} className={`cursor-pointer hover:bg-[var(--color-surface-muted)] ${filter.family === f.family ? "bg-[var(--color-surface-muted)]" : ""}`} onClick={() => toggle({ family: f.family })} data-testid={`steel-family-${f.family}`}>
                  <td>{f.label}</td>
                  <td className="text-right">{f.members}</td>
                  <td className="text-right" title={rangeText(f.kg_low, f.kg_high, f.kg) || undefined}>{kgText(f.kg)}</td>
                  <td className="text-right">{f.concrete_m3 === null ? "-" : f.concrete_m3.toLocaleString("en-US", { maximumFractionDigits: 2 })}</td>
                  <td>
                    {intensityText(f)}{" "}
                    {f.status ? <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${TONE[STATUS_TONE[f.status]]}`} title={t(`drawings.steelSummary.status.${f.status}`, STATUS_WORDS[f.status])}>{f.status === "IN_RANGE" ? t("drawings.steelSummary.inRange", "in range") : f.status === "BELOW_RANGE" ? t("drawings.steelSummary.below", "low") : t("drawings.steelSummary.above", "high")}</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div data-testid="steel-marks">
            <p className="pb-1 font-semibold">
              {filterWords(filter, labelOf) ? t("drawings.steelSummary.marksOf", "Marks: {{what}}", { what: filterWords(filter, labelOf) }) : t("drawings.steelSummary.marksAll", "All marks")}
              {" "}({marks.length})
              {filter.family || filter.dia ? <button type="button" className="ml-3 text-[12px] font-semibold text-[var(--color-trace-gold-dark)] underline" onClick={() => setFilter({})} data-testid="steel-clear">{t("drawings.steelSummary.clear", "Show all")}</button> : null}
            </p>
            <table className="w-full text-[12px]">
              <thead>
                <tr className="text-left text-[var(--color-text-muted)]">
                  <th className="font-medium">{t("drawings.steelSummary.mark", "Mark")}</th>
                  <th className="font-medium">{t("drawings.steelSummary.kind", "Kind")}</th>
                  <th className="font-medium">{t("drawings.steelSummary.floor", "Floor")}</th>
                  <th className="text-right font-medium">{t("drawings.steelSummary.count", "No.")}</th>
                  <th className="text-right font-medium">{filter.dia ? t("drawings.steelSummary.weightDia", "kg of {{dia}}", { dia: diaText(filter.dia) }) : t("drawings.steelSummary.weight", "Weight (kg)")}</th>
                  <th className="text-right font-medium">{t("drawings.steelSummary.each", "Each (kg)")}</th>
                  <th className="text-right font-medium">kg/m3</th>
                  <th className="font-medium">{t("drawings.steelSummary.basis", "Basis")}</th>
                </tr>
              </thead>
              <tbody>
                {marks.map((m, n) => (
                  <tr key={`${m.family}-${m.tag}-${m.level}-${m.basis}-${n}`} data-testid={`steel-mark-${m.tag}`}>
                    <td title={Object.entries(m.dia).map(([d, k]) => `${diaText(d)}: ${kgText(k)} kg`).join("\n") || undefined}>{m.tag}</td>
                    <td>{labelOf(m.family)}</td>
                    <td>{m.level || "-"}</td>
                    <td className="text-right">{m.count}</td>
                    <td className="text-right">{kgText(filter.dia ? diaKgOf(m, filter.dia) : m.kg)}</td>
                    <td className="text-right">{kgText(m.kg_each)}</td>
                    <td className="text-right">{m.kg_per_m3 === null ? "-" : m.kg_per_m3.toFixed(1)}</td>
                    <td><span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${TONE[BASIS_TONE[m.basis]]}`}>{BASIS_WORDS[m.basis]}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {s.marks_truncated ? <p className="pt-1 text-[var(--color-text-muted)]">{t("drawings.steelSummary.truncated", "Only the first {{n}} of {{total}} marks are listed.", { n: s.marks.length, total: s.marks_total })}</p> : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
