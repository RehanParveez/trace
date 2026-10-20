import { Badge } from "../../organizations/components/OrganizationUi";
import type { LedgerTrace } from "../types/drawings-boq.types";
import { sourceView } from "../utils/oneTotal";

export function SourceBadge({ kind, trace }: { kind: string; trace?: LedgerTrace | null }) {
  const v = sourceView(kind, trace);
  return (
    <span className="inline-flex flex-col gap-0.5" data-testid="source-badge" data-source={kind}>
      <Badge tone={v.tone}>{v.label}</Badge>
      {v.note ? <span className="text-[10.5px] text-[var(--color-text-muted)]" data-testid="source-badge-note">{v.note}</span> : null}
    </span>
  );
}
