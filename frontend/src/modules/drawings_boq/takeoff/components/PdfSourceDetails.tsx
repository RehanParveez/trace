import { Link } from "react-router-dom";
import { Badge } from "../../../organizations/components/OrganizationUi";

interface Props {
  inputs: Record<string, unknown> | undefined;
  projectId?: string;
}

const text = (v: unknown): string | null => (v === null || v === undefined || v === "" ? null : String(v));

const SOURCE: Record<string, string> = { MANUAL: "measured by hand", VECTOR_SNAP: "snapped to the drawing lines", TAG_SCAN: "counted from tags", PRINTED: "read from the printed area table" };
const DECISION: Record<string, string> = {
  COUNTED: "counted in the BOQ",
  VERIFIED: "only verified the model",
  REPLACED_MODEL: "replaced the model quantity",
  SKIPPED: "not counted",
};

export function PdfSourceDetails({ inputs, projectId }: Props) {
  if (!inputs) return null;
  const measurementId = text(inputs.measurement_id);
  const sheetId = text(inputs.sheet_id);
  const drawingId = text(inputs.drawing_id);
  const page = text(inputs.page_no);
  const cal = (inputs.calibration ?? null) as Record<string, unknown> | null;
  const rec = (inputs.reconciliation ?? null) as Record<string, unknown> | null;
  const source = text(inputs.source);
  const decision = text(rec?.decision);
  const href = projectId && drawingId && measurementId ? `/app/takeoff/${projectId}/${drawingId}?sheet=${sheetId ?? ""}&m=${measurementId}` : null;
  return (
    <div className="space-y-1 rounded-[7px] bg-[var(--color-surface-muted)] p-2.5 text-[11.5px] text-[var(--color-text-secondary)]" data-testid="pdf-source">
      <div className="flex flex-wrap items-center gap-2">
        {page ? <Badge tone="slate">page {page}</Badge> : null}
        {text(inputs.content_kind) ? <Badge tone={inputs.content_kind === "RASTER" ? "gold" : "slate"}>{String(inputs.content_kind).toLowerCase()}</Badge> : null}
        {source ? <span>{SOURCE[source] ?? source}</span> : null}
        {text(inputs.tag) ? <span className="font-mono">tag {String(inputs.tag)}</span> : null}
        {href ? <Link to={href} className="ml-auto font-semibold text-[var(--color-info)]">Open on drawing</Link> : null}
      </div>
      {cal ? (
        <div>
          Scale: {text(cal.method)?.replace("_", " ").toLowerCase()} · {text(cal.mm_per_pt)} mm/pt
          {text(cal.check_error_pct) ? ` · checked, off by ${text(cal.check_error_pct)}%` : " · no check dimension"}
          {text(cal.quality_factor) ? ` · quality factor ${text(cal.quality_factor)}` : ""}
        </div>
      ) : null}
      {decision ? (
        <div>
          Against the model: {DECISION[decision] ?? decision}
          {text(rec?.model_quantity) ? ` · model ${text(rec?.model_quantity)}` : ""}
          {text(rec?.variance_pct) ? ` · difference ${text(rec?.variance_pct)}%` : ""}
        </div>
      ) : null}
    </div>
  );
}
