import { Badge } from "../../../organizations/components/OrganizationUi";
import { runModeTone } from "../utils/recalculation.utils";
import { useScaleT } from "../utils/useRecalculationT";

export function RunModeBadge({ mode, fallbackReason }: { mode: string | undefined; fallbackReason?: string }) {
  const t = useScaleT();
  if (!mode) return null;
  const incremental = mode === "INCREMENTAL";
  const title = incremental
    ? t("scale.mode.incrementalHint", "Only what changed since the earlier run was recalculated.")
    : fallbackReason
      ? t("scale.mode.fullFallbackHint", "Everything was calculated because a partial update was not possible.")
      : t("scale.mode.fullHint", "Everything was calculated.");
  return (
    <span title={title}>
      <Badge tone={runModeTone(mode)}>
        {incremental ? t("scale.mode.incremental", "Incremental") : t("scale.mode.full", "Full")}
      </Badge>
    </span>
  );
}
