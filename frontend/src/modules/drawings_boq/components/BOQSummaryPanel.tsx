import { Badge, Button, Icon, Panel } from "../../organizations/components/OrganizationUi";
import { useBOQSummary, useExportBOQ, useGenerateLabourItems } from "../hooks";
import type { BOQVersion } from "../types/drawings-boq.types";
import { formatCurrency } from "../utils/drawings-boq.utils";

interface BOQSummaryPanelProps {
  version: BOQVersion;
  canUpdate: boolean;
  canAddItem: boolean;
  canExport: boolean;
  onEditDetails: () => void;
  onAddLineItem: () => void;
}

export function BOQSummaryPanel({ version, canUpdate, canAddItem, canExport, onEditDetails, onAddLineItem }: BOQSummaryPanelProps) {
  const summaryQuery = useBOQSummary(version.id);
  const generateLabour = useGenerateLabourItems(version.id);
  const exportBOQ = useExportBOQ(version.id, version.label);

  const summary = summaryQuery.data;

  return (
    <Panel className="space-y-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Grand total</span>
          <div className="text-[20px] font-bold text-[#191410]">{summary ? formatCurrency(summary.grand_total) : "—"}</div>
          {summary?.cost_per_sqft ? <span className="text-[10.5px] text-[#6b6152]">{formatCurrency(summary.cost_per_sqft)} / Sft</span> : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {canUpdate ? (
            <Button variant="ghost" size="sm" onClick={onEditDetails}>
              <Icon name="edit" size={12} />BOQ details
            </Button>
          ) : null}
          {canAddItem ? (
            <Button variant="ghost" size="sm" onClick={onAddLineItem}>
              <Icon name="plus" size={12} />Add line item
            </Button>
          ) : null}
          {canUpdate ? (
            <Button variant="ghost" size="sm" disabled={generateLabour.isPending || !version.covered_area_sqft} onClick={() => generateLabour.mutate()}>
              {generateLabour.isPending ? "Generating…" : "Generate labour"}
            </Button>
          ) : null}
          {canExport ? (
            <>
              <Button variant="ghost" size="sm" disabled={exportBOQ.isPending} onClick={() => exportBOQ.mutate("pdf")}>Export PDF</Button>
              <Button variant="ghost" size="sm" disabled={exportBOQ.isPending} onClick={() => exportBOQ.mutate("xlsx")}>Export Excel</Button>
            </>
          ) : null}
        </div>
      </div>

      {summary && !version.covered_area_sqft ? (
        <div className="rounded-[8px] border border-[#e6dcc0] bg-[#fbf6e8] px-3 py-2 text-[11px] text-[#8a6d1f]">
          Set a covered area in BOQ details to enable labour generation and cost-per-Sft.
        </div>
      ) : null}

      {summary ? (
        <div className="grid grid-cols-3 gap-3 border-t border-[#e1d5bc] pt-4 text-[11px]">
          <div>
            <span className="block text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Materials</span>
            <span className="font-mono text-[#191410]">{formatCurrency(summary.materials_total)}</span>
          </div>
          <div>
            <span className="block text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Labour</span>
            <span className="font-mono text-[#191410]">{formatCurrency(summary.labour_total)}</span>
          </div>
          <div>
            <span className="block text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Additional</span>
            <span className="font-mono text-[#191410]">{formatCurrency(summary.custom_total)}</span>
          </div>
        </div>
      ) : null}

      {summary ? (
        <p className="border-t border-[#e1d5bc] pt-3 text-[10.5px] italic text-[#756957]">In words: {summary.amount_in_words}</p>
      ) : null}

      {summary && (summary.unpriced_item_count > 0 || summary.unapproved_item_count > 0) ? (
        <div className="flex flex-wrap gap-2 border-t border-[#e1d5bc] pt-3">
          {summary.unpriced_item_count > 0 ? <Badge tone="red">{summary.unpriced_item_count} item(s) missing a rate</Badge> : null}
          {summary.unapproved_item_count > 0 ? <Badge tone="gold">{summary.unapproved_item_count} item(s) not yet approved</Badge> : null}
        </div>
      ) : null}
    </Panel>
  );
}