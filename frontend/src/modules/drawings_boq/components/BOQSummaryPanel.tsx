import { useState } from "react";
import { Badge, Button, ErrorState, Icon, Panel } from "../../organizations/components/OrganizationUi";
import { useBOQSummary, useExportBOQ, useGenerateLabourItems } from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { BOQVersion } from "../types/drawings-boq.types";
import { formatCurrency } from "../utils/drawings-boq.utils";
import { useTranslation } from "react-i18next";

interface BOQSummaryPanelProps {
  version: BOQVersion;
  canUpdate: boolean;
  canAddItem: boolean;
  canExport: boolean;
  onEditDetails: () => void;
  onAddLineItem: () => void;
}

export function BOQSummaryPanel({ version, canUpdate, canAddItem, canExport, onEditDetails, onAddLineItem }: BOQSummaryPanelProps) {
  const { t } = useTranslation();
  const summaryQuery = useBOQSummary(version.id);
  const generateLabour = useGenerateLabourItems(version.id);
  const exportBOQ = useExportBOQ(version.id, version.label);
  const [actionError, setActionError] = useState<string | null>(null);

  const summary = summaryQuery.data;

  if (summaryQuery.isError) {
    return (
      <ErrorState
        title={t("boq.summary.loadError")}
        onRetry={() => void summaryQuery.refetch()}
      />
    );
  }

  return (
    <Panel className="space-y-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">{t("boq.summary.grandTotal")}</span>
          <div className="text-[20px] font-bold text-[#191410]">{summary ? formatCurrency(summary.grand_total) : "—"}</div>
          {summary?.cost_per_sqft ? <span className="text-[10.5px] text-[#6b6152]">{formatCurrency(summary.cost_per_sqft)} / Sft</span> : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {canUpdate ? (
            <Button variant="ghost" size="sm" onClick={onEditDetails}>
              <Icon name="edit" size={12} />{t("boq.summary.boqDetails")}
            </Button>
          ) : null}
          {canAddItem ? (
            <Button variant="ghost" size="sm" onClick={onAddLineItem}>
              <Icon name="plus" size={12} />{t("boq.summary.addLineItem")}
            </Button>
          ) : null}

          {canUpdate ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={generateLabour.isPending || !version.covered_area_sqft}
              onClick={() => {
                setActionError(null);
                generateLabour.mutate(undefined, {
                  onError: (error) =>
                    setActionError(getApiErrorMessage(error, t("boq.summary.generateError")))
                });
              }}
            >
              {generateLabour.isPending ? t("boq.summary.generating") : t("boq.summary.generateLabour")}
            </Button>
          ) : null}
          {canExport ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                disabled={exportBOQ.isPending}
                onClick={() => {
                  setActionError(null);
                  exportBOQ.mutate("pdf", {
                    onError: (error) =>
                      setActionError(getApiErrorMessage(error, t("boq.summary.exportPdfError")))
                  });
                }}
              >
                {t("boq.summary.exportPdf")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={exportBOQ.isPending}
                onClick={() => {
                  setActionError(null);
                  exportBOQ.mutate("xlsx", {
                    onError: (error) =>
                      setActionError(getApiErrorMessage(error, t("boq.summary.exportExcelError")))
                  });
                }}
              >
                {t("boq.summary.exportExcel")}
              </Button>
            </>
          ) : null}
        </div>
      </div>

      {actionError ? (
        <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">
          {actionError}
        </div>
      ) : null}

      {summary && !version.covered_area_sqft ? (
        <div className="rounded-[8px] border border-[#e6dcc0] bg-[#fbf6e8] px-3 py-2 text-[11px] text-[#8a6d1f]">
          {t("boq.summary.coveredAreaHint")}
        </div>
      ) : null}

      {summary ? (
        <div className="grid grid-cols-3 gap-3 border-t border-[#e1d5bc] pt-4 text-[11px]">
          <div>
            <span className="block text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">{t("boq.summary.materials")}</span>
            <span className="font-mono text-[#191410]">{formatCurrency(summary.materials_total)}</span>
          </div>
          <div>
            <span className="block text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">{t("boq.summary.labour")}</span>
            <span className="font-mono text-[#191410]">{formatCurrency(summary.labour_total)}</span>
          </div>
          <div>
            <span className="block text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">{t("boq.summary.additional")}</span>
            <span className="font-mono text-[#191410]">{formatCurrency(summary.custom_total)}</span>
          </div>
        </div>
      ) : null}

      {summary ? (
        <p className="border-t border-[#e1d5bc] pt-3 text-[10.5px] italic text-[#756957]">{t("boq.summary.inWords")}: {summary.amount_in_words}</p>
      ) : null}

      {summary && (summary.unpriced_item_count > 0 || summary.unapproved_item_count > 0) ? (
        <div className="flex flex-wrap gap-2 border-t border-[#e1d5bc] pt-3">
          {summary.unpriced_item_count > 0 ? <Badge tone="red">{t("boq.summary.unpriced", { count: summary.unpriced_item_count })}</Badge> : null}
          {summary.unapproved_item_count > 0 ? <Badge tone="gold">{t("boq.summary.unapproved", { count: summary.unapproved_item_count })}</Badge> : null}
        </div>
      ) : null}
    </Panel>
  );
}