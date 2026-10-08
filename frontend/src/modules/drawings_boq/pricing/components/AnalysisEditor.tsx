import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {Button, Field, inputClass, Panel, PanelHeader, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { useLabourRates, useMaterialLibrary } from "../../hooks";
import { formatCurrency, formatQuantity } from "../../utils/drawings-boq.utils";
import { useCreateAnalysis, useRateItems, useUpdateAnalysis } from "../hooks";
import type {AnalysisComponentInput, AnalysisComponentSource, AnalysisComponentType, RateAnalysis, RateBook, RateItem,
} from "../types/pricing.types";
import {COMPONENT_SOURCES, COMPONENT_SOURCE_LABEL, COMPONENT_TYPES, COMPONENT_TYPE_LABEL, parseNonNegative, previewAnalysisRate,
} from "../utils/pricing.utils";
import { FormError } from "./FormError";

interface DraftComponent {
  key: string;
  component_type: AnalysisComponentType;
  description: string;
  work_item_code: string;
  rate_source: AnalysisComponentSource;
  ref_rate_item_id: string;
  unit: string;
  coefficient: string;
  unit_rate: string;
}

let draftCounter = 0;
const nextKey = () => `c${(draftCounter += 1)}`;

function blankComponent(): DraftComponent {
  return {
    key: nextKey(), component_type: "MATERIAL", description: "", work_item_code: "", rate_source: "DIRECT",
    ref_rate_item_id: "", unit: "", coefficient: "1", unit_rate: "",
  };
}

function fromAnalysis(analysis: RateAnalysis): DraftComponent[] {
  return [...analysis.components]
    .sort((a, b) => a.sequence - b.sequence)
    .map((c) => ({
      key: nextKey(),
      component_type: c.component_type,
      description: c.description,
      work_item_code: c.work_item_code ?? "",
      rate_source: c.rate_source,
      ref_rate_item_id: c.ref_rate_item_id ?? "",
      unit: c.unit,
      coefficient: String(Number(c.coefficient)),
      unit_rate: c.unit_rate === null ? "" : String(Number(c.unit_rate)),
    }));
}

const sameUnit = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

interface AnalysisEditorProps {
  book: RateBook;
  analysis?: RateAnalysis | null;
  onClose: () => void;
}

export function AnalysisEditor({ book, analysis, onClose }: AnalysisEditorProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const createAnalysis = useCreateAnalysis(book.id);
  const updateAnalysis = useUpdateAnalysis(book.id);
  const rateItems = useRateItems(book.id, {});
  const labourRates = useLabourRates();
  const library = useMaterialLibrary();
  const editing = Boolean(analysis);

  const [code, setCode] = useState(analysis?.code ?? "");
  const [workItemCode, setWorkItemCode] = useState(analysis?.work_item_code ?? "");
  const [description, setDescription] = useState(analysis?.description ?? "");
  const [unit, setUnit] = useState(analysis?.unit ?? "m3");
  const [basis, setBasis] = useState(analysis ? String(Number(analysis.basis_quantity)) : "1");
  const [overhead, setOverhead] = useState(analysis ? String(Number(analysis.overhead_pct)) : "0");
  const [profit, setProfit] = useState(analysis ? String(Number(analysis.profit_pct)) : "0");
  const [components, setComponents] = useState<DraftComponent[]>(analysis ? fromAnalysis(analysis) : [blankComponent()]);
  const [error, setError] = useState<string | null>(null);

  const pending = createAnalysis.isPending || updateAnalysis.isPending;
  const itemsById = useMemo(() => new Map<string, RateItem>(rateItems.items.map((i) => [i.id, i])), [rateItems.items]);

  function patch(key: string, change: Partial<DraftComponent>) {
    setComponents((rows) => rows.map((row) => (row.key === key ? { ...row, ...change } : row)));
  }

  function changeSource(key: string, source: AnalysisComponentSource) {
    patch(key, { rate_source: source, ref_rate_item_id: "", unit_rate: "" });
  }

  function pickRateItem(key: string, id: string) {
    const item = itemsById.get(id);
    setComponents((rows) =>
      rows.map((row) =>
        row.key !== key
          ? row
          : {
              ...row,
              ref_rate_item_id: id,
              description: row.description || item?.description || item?.work_item_code || "",
              unit: item?.unit ?? row.unit,
              work_item_code: item?.work_item_code ?? row.work_item_code,
            },
      ),
    );
  }

  function pickLabour(key: string, id: string) {
    const rate = (labourRates.data ?? []).find((r) => r.id === id);
    if (!rate) return;
    patch(key, { description: rate.trade, unit: rate.unit, work_item_code: rate.work_item_code ?? "", component_type: "LABOUR" });
  }

  function pickLibrary(key: string, id: string) {
    const entry = (library.data ?? []).find((r) => r.id === id);
    if (!entry) return;
    patch(key, {
      description: entry.raw_text,
      unit: entry.default_unit ?? "",
      work_item_code: entry.work_item_code ?? "",
      component_type: "MATERIAL",
    });
  }

  function knownRate(row: DraftComponent): number | null {
    if (row.rate_source === "DIRECT") return parseNonNegative(row.unit_rate);
    if (row.rate_source === "RATE_ITEM") {
      const item = itemsById.get(row.ref_rate_item_id);
      return item && sameUnit(item.unit, row.unit) ? Number(item.rate) : null;
    }
    if (row.rate_source === "LABOUR_RATE") {
      const match = (labourRates.data ?? []).find(
        (r) => (row.work_item_code && r.work_item_code === row.work_item_code) || r.trade.trim().toLowerCase() === row.description.trim().toLowerCase(),
      );
      return match && sameUnit(match.unit, row.unit) ? Number(match.rate) : null;
    }
    const match = (library.data ?? []).find(
      (r) => (row.work_item_code && r.work_item_code === row.work_item_code) || r.raw_text.trim().toLowerCase() === row.description.trim().toLowerCase(),
    );
    return match && match.default_rate !== null && sameUnit(match.default_unit ?? row.unit, row.unit) ? Number(match.default_rate) : null;
  }

  const basisValue = parseNonNegative(basis);
  const overheadValue = parseNonNegative(overhead);
  const profitValue = parseNonNegative(profit);
  const lineRates = components.map((row) => ({ coefficient: parseNonNegative(row.coefficient) ?? 0, unit_rate: knownRate(row) }));
  const preview =
    basisValue && basisValue > 0 && overheadValue !== null && profitValue !== null && components.length > 0
      ? previewAnalysisRate(lineRates, basisValue, overheadValue, profitValue)
      : null;

  function rowProblem(row: DraftComponent): string | null {
    if (!row.description.trim() || !row.unit.trim()) return t("pricing.analysis.rowIncomplete", "Each component needs a description and a unit.");
    if (parseNonNegative(row.coefficient) === null) return t("pricing.analysis.coefInvalid", "The coefficient must be zero or more.");
    if (row.rate_source === "DIRECT" && parseNonNegative(row.unit_rate) === null) return t("pricing.analysis.directNeedsRate", "A typed-rate component needs a rate.");
    if (row.rate_source === "RATE_ITEM" && !row.ref_rate_item_id) return t("pricing.analysis.itemNeeded", "Pick the rate this component uses.");
    return null;
  }

  const firstProblem = components.map(rowProblem).find(Boolean) ?? null;
  const formInvalid =
    !description.trim() || !unit.trim() || basisValue === null || basisValue <= 0 || overheadValue === null ||
    profitValue === null || (!editing && (!code.trim() || !workItemCode.trim())) || components.length === 0 || firstProblem !== null;

  function toInput(row: DraftComponent): AnalysisComponentInput {
    return {
      component_type: row.component_type,
      description: row.description.trim(),
      work_item_code: row.work_item_code.trim().toUpperCase() || null,
      rate_source: row.rate_source,
      ref_rate_item_id: row.rate_source === "RATE_ITEM" ? row.ref_rate_item_id : null,
      unit: row.unit.trim(),
      coefficient: parseNonNegative(row.coefficient) ?? 0,
      unit_rate: row.rate_source === "DIRECT" ? parseNonNegative(row.unit_rate) : null,
    };
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (formInvalid || basisValue === null || overheadValue === null || profitValue === null) return;
    const common = {
      description: description.trim(),
      unit: unit.trim(),
      basis_quantity: basisValue,
      overhead_pct: overheadValue,
      profit_pct: profitValue,
      components: components.map(toInput),
    };

    if (analysis) {
      updateAnalysis.mutate(
        { analysisId: analysis.id, payload: common },
        {
          onSuccess: () => {
            showToast({ tone: "success", title: t("pricing.analysis.savedToast", "Analysis saved") });
            onClose();
          },
          onError: (e) => setError(getApiErrorMessage(e, t("pricing.analysis.saveError", "Couldn't save this analysis."))),
        },
      );
      return;
    }
    createAnalysis.mutate(
      { ...common, code: code.trim().toUpperCase(), work_item_code: workItemCode.trim().toUpperCase() },
      {
        onSuccess: () => {
          showToast({ tone: "success", title: t("pricing.analysis.createdToast", "Analysis created") });
          onClose();
        },
        onError: (e) => setError(getApiErrorMessage(e, t("pricing.analysis.createError", "Couldn't create this analysis."))),
      },
    );
  }

  const small =
    "w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-2 text-[12.5px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)] disabled:bg-[var(--color-surface-muted)]";
  const smallLabel = "mb-1 block text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

  return (
    <form onSubmit={submit}>
      <Panel>
        <PanelHeader
          eyebrow={t("pricing.analysis.eyebrow", "RATE ANALYSIS")}
          title={editing ? t("pricing.analysis.editTitle", "Edit analysis {{code}}", { code: analysis?.code }) : t("pricing.analysis.newTitle", "New rate analysis")}
          description={t(
            "pricing.analysis.desc",
            "Build a rate from its parts: quantity coefficients × component rates, plus overhead and profit, divided by the basis quantity. Apply it to the book's rates once it reads right.",
          )}
        />

        <div className="space-y-4 p-5">
          <div className="grid gap-4 sm:grid-cols-4">
            <Field label={t("pricing.analysis.code", "Analysis code")} hint={editing ? t("pricing.analysis.codeLocked", "The code can't change.") : undefined}>
              <input required disabled={editing} className={inputClass} value={code} maxLength={80} onChange={(e) => setCode(e.target.value)} placeholder="AN-RCC-M20" />
            </Field>
            <Field label={t("pricing.analysis.workItem", "Work item code")} hint={editing ? t("pricing.analysis.workItemLocked", "Fixed once created.") : t("pricing.analysis.workItemHint", "The rate it produces.")}>
              <input required disabled={editing} className={inputClass} value={workItemCode} maxLength={50} onChange={(e) => setWorkItemCode(e.target.value)} placeholder="RCC-M20" />
            </Field>
            <Field label={t("pricing.analysis.unit", "Rate unit")}>
              <input required className={inputClass} value={unit} maxLength={20} onChange={(e) => setUnit(e.target.value)} />
            </Field>
            <Field label={t("pricing.analysis.basis", "Basis quantity")} hint={t("pricing.analysis.basisHint", "Quantity the parts below make.")}>
              <input required type="number" min="0.0001" step="any" className={inputClass} value={basis} onChange={(e) => setBasis(e.target.value)} />
            </Field>
          </div>
          <Field label={t("pricing.analysis.description", "Description")}>
            <input required className={inputClass} value={description} maxLength={500} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("pricing.analysis.overhead", "Overhead %")} hint={t("pricing.analysis.overheadHint", "On the cost of the parts.")}>
              <input type="number" min="0" step="any" className={inputClass} value={overhead} onChange={(e) => setOverhead(e.target.value)} />
            </Field>
            <Field label={t("pricing.analysis.profit", "Profit %")} hint={t("pricing.analysis.profitHint", "On cost plus overhead.")}>
              <input type="number" min="0" step="any" className={inputClass} value={profit} onChange={(e) => setProfit(e.target.value)} />
            </Field>
          </div>

          <div>
            <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
              {t("pricing.analysis.components", "Components")}
            </div>
            <div className="space-y-3">
              {components.map((row, index) => {
                const rate = knownRate(row);
                const coefficient = parseNonNegative(row.coefficient);
                const rateItemOptions = rateItems.items;
                return (
                  <div key={row.key} className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
                    <div className="grid gap-3 sm:grid-cols-12">
                      <label className="sm:col-span-2">
                        <span className={smallLabel}>{t("pricing.analysis.type", "Type")}</span>
                        <select className={small} value={row.component_type} onChange={(e) => patch(row.key, { component_type: e.target.value as AnalysisComponentType })}>
                          {COMPONENT_TYPES.map((ct) => (
                            <option key={ct} value={ct}>{t(`pricing.componentType.${ct}`, COMPONENT_TYPE_LABEL[ct])}</option>
                          ))}
                        </select>
                      </label>
                      <label className="sm:col-span-3">
                        <span className={smallLabel}>{t("pricing.analysis.rateFrom", "Rate comes from")}</span>
                        <select className={small} value={row.rate_source} onChange={(e) => changeSource(row.key, e.target.value as AnalysisComponentSource)}>
                          {COMPONENT_SOURCES.map((s) => (
                            <option key={s} value={s}>{t(`pricing.componentSource.${s}`, COMPONENT_SOURCE_LABEL[s])}</option>
                          ))}
                        </select>
                      </label>
                      <div className="sm:col-span-7">
                        {row.rate_source === "DIRECT" ? (
                          <label>
                            <span className={smallLabel}>{t("pricing.analysis.unitRate", "Rate per unit")}</span>
                            <input type="number" min="0" step="0.01" className={small} value={row.unit_rate} onChange={(e) => patch(row.key, { unit_rate: e.target.value })} />
                          </label>
                        ) : null}
                        {row.rate_source === "RATE_ITEM" ? (
                          <label>
                            <span className={smallLabel}>{t("pricing.analysis.pickItem", "Rate in this book")}</span>
                            <select className={small} value={row.ref_rate_item_id} onChange={(e) => pickRateItem(row.key, e.target.value)}>
                              <option value="">{t("pricing.analysis.choose", "Choose…")}</option>
                              {rateItemOptions.map((i) => (
                                <option key={i.id} value={i.id}>
                                  {i.work_item_code} · {i.unit} · {formatCurrency(i.rate)}
                                </option>
                              ))}
                            </select>
                            {rateItems.hasNextPage ? (
                              <button type="button" className="mt-1 text-[11.5px] font-semibold text-[var(--color-info)]" onClick={() => void rateItems.fetchNextPage()}>
                                {t("pricing.analysis.loadMoreRates", "Load more rates")}
                              </button>
                            ) : null}
                          </label>
                        ) : null}
                        {row.rate_source === "LABOUR_RATE" ? (
                          <label>
                            <span className={smallLabel}>{t("pricing.analysis.pickLabour", "Labour rate")}</span>
                            <select className={small} value="" onChange={(e) => pickLabour(row.key, e.target.value)}>
                              <option value="">{row.description ? row.description : t("pricing.analysis.choose", "Choose…")}</option>
                              {(labourRates.data ?? []).map((r) => (
                                <option key={r.id} value={r.id}>{r.trade} · {r.unit} · {formatCurrency(r.rate)}</option>
                              ))}
                            </select>
                          </label>
                        ) : null}
                        {row.rate_source === "MATERIAL_LIBRARY" ? (
                          <label>
                            <span className={smallLabel}>{t("pricing.analysis.pickLibrary", "Material library entry")}</span>
                            <select className={small} value="" onChange={(e) => pickLibrary(row.key, e.target.value)}>
                              <option value="">{row.description ? row.description : t("pricing.analysis.choose", "Choose…")}</option>
                              {(library.data ?? []).filter((r) => r.default_rate !== null).map((r) => (
                                <option key={r.id} value={r.id}>{r.raw_text} · {r.default_unit ?? "—"} · {formatCurrency(r.default_rate)}</option>
                              ))}
                            </select>
                          </label>
                        ) : null}
                      </div>

                      <label className="sm:col-span-5">
                        <span className={smallLabel}>{t("pricing.analysis.componentDescription", "Description")}</span>
                        <input className={small} value={row.description} maxLength={500} onChange={(e) => patch(row.key, { description: e.target.value })} />
                      </label>
                      <label className="sm:col-span-2">
                        <span className={smallLabel}>{t("pricing.analysis.coefficient", "Coefficient")}</span>
                        <input type="number" min="0" step="any" className={small} value={row.coefficient} onChange={(e) => patch(row.key, { coefficient: e.target.value })} />
                      </label>
                      <label className="sm:col-span-2">
                        <span className={smallLabel}>{t("pricing.analysis.componentUnit", "Unit")}</span>
                        <input className={small} value={row.unit} maxLength={20} onChange={(e) => patch(row.key, { unit: e.target.value })} />
                      </label>
                      <div className="flex items-end justify-between gap-2 sm:col-span-3">
                        <div className="text-[12px] text-[var(--color-text-secondary)]">
                          <div className={smallLabel}>{t("pricing.analysis.lineAmount", "Line amount")}</div>
                          <div className="font-mono">
                            {rate !== null && coefficient !== null
                              ? formatCurrency(Math.round((coefficient * rate + Number.EPSILON) * 100) / 100)
                              : t("pricing.analysis.atSave", "Set by the server")}
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={components.length === 1}
                          aria-label={t("pricing.analysis.removeComponent", "Remove component {{n}}", { n: index + 1 })}
                          onClick={() => setComponents((rows) => rows.filter((r) => r.key !== row.key))}
                        >
                          {t("pricing.analysis.remove", "Remove")}
                        </Button>
                      </div>

                      {row.rate_source === "LABOUR_RATE" || row.rate_source === "MATERIAL_LIBRARY" ? (
                        <label className="sm:col-span-4">
                          <span className={smallLabel}>{t("pricing.analysis.matchCode", "Match on work item code (optional)")}</span>
                          <input className={small} value={row.work_item_code} maxLength={50} onChange={(e) => patch(row.key, { work_item_code: e.target.value })} />
                        </label>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-3">
              <Button type="button" variant="secondary" size="sm" onClick={() => setComponents((rows) => [...rows, blankComponent()])}>
                {t("pricing.analysis.addComponent", "Add component")}
              </Button>
            </div>
          </div>

          <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-[13px]">
            {preview !== null ? (
              <span>
                {t("pricing.analysis.preview", "Rate per {{unit}}: {{rate}} for a basis of {{basis}}.", {
                  unit, rate: formatCurrency(preview), basis: formatQuantity(basisValue ?? 0),
                })}{" "}
                <span className="text-[var(--color-text-muted)]">{t("pricing.analysis.previewNote", "Preview only; the saved breakdown is the figure of record.")}</span>
              </span>
            ) : (
              <span className="text-[var(--color-text-secondary)]">
                {t("pricing.analysis.noPreview", "The rate is worked out on the server once some component rates come from the book, labour rates or the library. Open the breakdown after saving.")}
              </span>
            )}
          </div>

          {firstProblem ? <div className="text-[12px] text-[var(--color-text-secondary)]">{firstProblem}</div> : null}
          <FormError message={error} />
        </div>

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] p-5">
          <Button type="button" variant="ghost" onClick={onClose} disabled={pending}>{t("common.cancel", "Cancel")}</Button>
          <Button type="submit" variant="primary" disabled={pending || formInvalid}>
            {pending ? t("common.saving", "Saving…") : t("pricing.analysis.save", "Save analysis")}
          </Button>
        </div>
      </Panel>
    </form>
  );
}
