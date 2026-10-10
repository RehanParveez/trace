import { useState } from "react";
import { Button } from "../../../organizations/components/OrganizationUi";
import { useScaleT } from "../utils/useRecalculationT";
import { ElementImpactDialog } from "./ElementImpactDialog";

export function ElementImpactButton({ runId, elementId }: { runId: string; elementId: string | null | undefined }) {
  const t = useScaleT();
  const [open, setOpen] = useState(false);
  if (!elementId) return <span className="text-[var(--color-text-muted)]">—</span>;
  return (
    <>
      <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
        {t("scale.impact.open", "Impact")}
      </Button>
      {open ? <ElementImpactDialog runId={runId} elementId={elementId} onClose={() => setOpen(false)} /> : null}
    </>
  );
}