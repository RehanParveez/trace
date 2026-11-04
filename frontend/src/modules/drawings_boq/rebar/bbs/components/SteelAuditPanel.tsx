import { SteelBoqCard } from "./SteelBoqCard";
import { SteelFiguresCard } from "./SteelFiguresCard";

interface Props {
  runId: string;
  projectId: string;
  versionId: string;
  canEdit: boolean;
  canAdjust: boolean;
}

export function SteelAuditPanel({ runId, projectId, versionId, canEdit, canAdjust }: Props) {
  return (
    <div className="space-y-3" data-testid="steel-audit-panel">
      <SteelFiguresCard runId={runId} projectId={projectId} canEdit={canEdit} />
      <SteelBoqCard versionId={versionId} canAdjust={canAdjust} />
    </div>
  );
}
