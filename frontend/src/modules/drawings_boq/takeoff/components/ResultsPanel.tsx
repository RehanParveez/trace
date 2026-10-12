import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../../organizations/components/OrganizationUi";
import type { Reconciliation, ReconMode } from "../types/takeoff.types";
import { fmtDecimal, fmtPct } from "../utils/format";

interface Props {
  data: Reconciliation | undefined;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  canEdit: boolean;
  onMode: (measurementId: string, mode: ReconMode) => void;
  onOpen: (sheetId: string | undefined, measurementId: string) => void;
  onGoToRun: () => void;
}

const DECISION_TEXT: Record<string, { tone: "green" | "gold" | "red" | "blue" | "slate"; text: string }> = {
  COUNTED: { tone: "green", text: "Counted in the BOQ" },
  VERIFIED: { tone: "blue", text: "Only verified the model" },
  REPLACED_MODEL: { tone: "gold", text: "Replaced the model" },
  SKIPPED: { tone: "red", text: "Not counted" },
};

export function ResultsPanel(p: Props) {
  const { t } = useTranslation();
  if (p.loading) return <LoadingState label={t("boq.takeoff.loading", "Loading…")} />;
  if (p.error) return <ErrorState title={t("boq.takeoff.results.error", "Couldn't load the results")} onRetry={p.onRetry} />;
  const data = p.data;
  if (!data || !data.run_id) {
    return (
      <div className="space-y-3 p-4 text-[13px] text-[var(--color-text-secondary)]" data-testid="results-empty">
        <p>{t("boq.takeoff.results.none", "No calculation has used these measurements yet. Confirm your measurements, then start a calculation run from the project page.")}</p>
        <button type="button" className="font-semibold text-[var(--color-info)]" onClick={p.onGoToRun}>{t("boq.takeoff.results.goRun", "Go to the calculation run")}</button>
      </div>
    );
  }
  const s = data.stats;
  return (
    <div className="space-y-3 p-4" data-testid="results-panel">
      <div className="flex flex-wrap gap-2 text-[12px]">
        <Badge tone="green">{s.counted ?? 0} {t("boq.takeoff.results.counted", "counted")}</Badge>
        <Badge tone="blue">{s.verified ?? 0} {t("boq.takeoff.results.verified", "verified")}</Badge>
        {Object.entries(s.skipped ?? {}).map(([k, v]) => (<Badge key={k} tone="red">{v} {k.toLowerCase().replace(/_/g, " ")}</Badge>))}
        {s.tolerance_pct ? <Badge tone="slate">{t("boq.takeoff.results.tolerance", "tolerance")} {s.tolerance_pct}%</Badge> : null}
      </div>
      {(s.not_counted ?? []).length > 0 ? (
        <div className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]">
          {t("boq.takeoff.results.notCounted", "These work items are already measured by the model, so your PDF measurements were not counted. Choose Add, Replace or Verify on each measurement below.")}
          <ul className="mt-1 list-disc ps-5 font-mono text-[12px]">{s.not_counted!.map((n) => (<li key={`${n.work_item_code}-${n.level_id}`}>{n.work_item_code} ({n.measurements})</li>))}</ul>
        </div>
      ) : null}
      {data.measurements.length === 0 ? <EmptyState icon="info" title={t("boq.takeoff.results.noRows", "No rows")} description="" /> : null}
      <ul className="space-y-2">
        {data.measurements.map((r) => {
          const d = DECISION_TEXT[r.decision ?? ""] ?? { tone: "slate" as const, text: r.decision ?? "" };
          return (
            <li key={r.measurement_id} className="rounded-[8px] border border-[var(--color-border)] p-2.5" data-testid="result-row">
              <div className="flex items-center gap-2">
                <button type="button" className="min-w-0 flex-1 truncate text-left text-[13px] font-semibold" onClick={() => p.onOpen(r.sheet_id, r.measurement_id)}>{r.label || r.tag || r.work_item_code || r.measurement_id.slice(0, 6)}</button>
                <Badge tone={d.tone}>{d.text}</Badge>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-x-3 text-[12px] text-[var(--color-text-secondary)]">
                <span>{r.work_item_code ?? "—"}</span>
                <span className="font-mono">{fmtDecimal(r.quantity, 3)} {r.unit}</span>
                {r.model_quantity ? <span>{t("boq.takeoff.results.model", "Model")}: <span className="font-mono">{fmtDecimal(r.model_quantity, 3)}</span></span> : null}
                {r.variance_pct ? <span>{t("boq.takeoff.results.variance", "Difference")}: <span className="font-mono">{fmtDecimal(r.variance_pct, 2)}%</span></span> : null}
                <span>{t("boq.takeoff.confidence", "Confidence")} {fmtPct(r.confidence)}</span>
              </div>
              {r.message ? <div className="mt-1 text-[12px] text-[var(--color-danger)]">{r.message}</div> : null}
              {p.canEdit && (r.decision === "VERIFIED" || r.decision === "SKIPPED") ? (
                <div className="mt-1.5 flex gap-2 text-[12px] font-semibold text-[var(--color-info)]">
                  <button type="button" onClick={() => p.onMode(r.measurement_id, "ADD")}>{t("boq.takeoff.recon.addShort", "Add to model")}</button>
                  <button type="button" onClick={() => p.onMode(r.measurement_id, "REPLACE_MODEL")}>{t("boq.takeoff.recon.replaceShort", "Replace model")}</button>
                  <button type="button" onClick={() => p.onMode(r.measurement_id, "VERIFY_ONLY")}>{t("boq.takeoff.recon.verifyShort", "Verify only")}</button>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
      <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.takeoff.results.rerun", "After changing a mode, run the calculation again to see the new result.")}</p>
    </div>
  );
}
