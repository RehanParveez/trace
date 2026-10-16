import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, ErrorState, LoadingState } from "../../../organizations/components/OrganizationUi";
import type { ColumnReconcile } from "../types/takeoff.types";
import { modelPlaceText, pdfPlaceText, placementText, reconcileState, sizeText } from "../utils/reconcile";

interface Props {
  data: ColumnReconcile | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  model: string | null;
  onModel: (id: string | null) => void;
  onShift: (dx: string, dy: string) => void;
}

export function ReconcilePanel({ data, loading, error, onRetry, model, onModel, onShift }: Props) {
  const { t } = useTranslation();
  const [dx, setDx] = useState("");
  const [dy, setDy] = useState("");
  if (loading) return <LoadingState label={t("boq.takeoff.reconcile.loading", "Comparing with the model…")} />;
  if (error) return <ErrorState title={t("boq.takeoff.reconcile.error", "Couldn't compare with the model")} onRetry={onRetry} />;
  const state = reconcileState(data);
  if (!data || state === "EMPTY" || state === "NO_MODEL" || state === "NO_PDF") {
    return (
      <div className="space-y-1 border-t border-[var(--color-border)] p-4 text-[12px] text-[var(--color-text-secondary)]" data-testid="reconcile-none" data-state={state}>
        <h3 className="font-semibold text-[var(--color-text)]">{t("boq.takeoff.reconcile.title", "PDF columns against the model")}</h3>
        {state === "NO_PDF"
          ? t("boq.takeoff.reconcile.noPdf", "No columns have been counted on this drawing yet.")
          : t("boq.takeoff.reconcile.noModel", "This project has no read IFC model with columns to compare with.")}
      </div>
    );
  }
  return (
    <div className="space-y-2 border-t border-[var(--color-border)] p-4 text-[12px]" data-testid="reconcile-panel" data-state={state}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.reconcile.title", "PDF columns against the model")}</h3>
        {state === "AGREES" ? <Badge tone="green">{t("boq.takeoff.reconcile.agrees", "agree")}</Badge> : state === "DIFFERS" ? <Badge tone="gold">{t("boq.takeoff.reconcile.differs", "differ")}</Badge> : <Badge tone="red">{t("boq.takeoff.reconcile.unmatched", "could not be put together")}</Badge>}
      </div>
      {data.models.length > 1 ? (
        <label className="flex items-center gap-2 text-[11.5px]">
          <span>{t("boq.takeoff.reconcile.model", "Model")}</span>
          <select className="rounded border border-[var(--color-border)] bg-transparent px-1 py-0.5" value={model ?? data.model_drawing_id ?? ""} onChange={(e) => onModel(e.target.value || null)} data-testid="reconcile-model">
            {data.models.map((m) => <option key={m.drawing_id} value={m.drawing_id}>{`${m.filename} (${m.columns})`}</option>)}
          </select>
        </label>
      ) : null}

      {state === "UNMATCHED" ? (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="reconcile-unmatched">
          {t("boq.takeoff.reconcile.unmatchedHelp", "The columns of the two did not line up on any shift. Give the shift that takes the PDF onto the model, in millimetres.")}
        </p>
      ) : (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="reconcile-placement">{placementText(data)}</p>
      )}
      <div className="flex flex-wrap items-center gap-1 text-[11.5px]">
        <span>{t("boq.takeoff.reconcile.shift", "Shift")}</span>
        <input className="w-20 rounded border border-[var(--color-border)] bg-transparent px-1 py-0.5" inputMode="decimal" placeholder="dx" value={dx} onChange={(e) => { setDx(e.target.value); onShift(e.target.value, dy); }} data-testid="reconcile-dx" />
        <input className="w-20 rounded border border-[var(--color-border)] bg-transparent px-1 py-0.5" inputMode="decimal" placeholder="dy" value={dy} onChange={(e) => { setDy(e.target.value); onShift(dx, e.target.value); }} data-testid="reconcile-dy" />
        <span className="text-[var(--color-text-muted)]">mm</span>
      </div>
      {state !== "UNMATCHED" ? (
        <p data-testid="reconcile-counts">
          {t("boq.takeoff.reconcile.counts", "{{pairs}} of {{pdf}} PDF places match a model column; the model has {{model}}.", { pairs: data.pairs.length + data.size_differs.length, pdf: data.pdf_places, model: data.model_places })}
        </p>
      ) : null}

      {data.size_differs.length > 0 ? (
        <section data-testid="reconcile-size">
          <div className="font-semibold">{t("boq.takeoff.reconcile.sizeDiffers", "Same place, different size")}</div>
          <ul className="list-disc pl-4 text-[11.5px]">{data.size_differs.map((s, i) => <li key={i}>{`${pdfPlaceText(s.pdf)}: ${sizeText(s.pdf_size)}; model ${modelPlaceText(s.model)}: ${sizeText(s.model_size)}`}</li>)}</ul>
        </section>
      ) : null}

      {data.pdf_only.length > 0 ? (
        <section data-testid="reconcile-pdf-only">
          <div className="font-semibold">{t("boq.takeoff.reconcile.pdfOnly", "Only in the PDF")}</div>
          <ul className="list-disc pl-4 text-[11.5px]">{data.pdf_only.map((p, i) => <li key={i}>{pdfPlaceText(p)}</li>)}</ul>
        </section>
      ) : null}

      {data.model_only.length > 0 ? (
        <section data-testid="reconcile-model-only">
          <div className="font-semibold">{t("boq.takeoff.reconcile.modelOnly", "Only in the model")}</div>
          <ul className="list-disc pl-4 text-[11.5px]">{data.model_only.map((p, i) => <li key={i}>{modelPlaceText(p)}</li>)}</ul>
        </section>
      ) : null}
    </div>
  );
}
