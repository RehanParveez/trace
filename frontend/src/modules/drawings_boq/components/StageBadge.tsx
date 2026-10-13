import { useTranslation } from "react-i18next";
import { Badge } from "../../organizations/components/OrganizationUi";
import { stageDescriptor } from "../utils/drawings-boq.utils";

export function useStageLabel(): (code: string) => string {
  const { t } = useTranslation();
  return (code: string) => {
    const d = stageDescriptor(code);
    return t(d.key, { defaultValue: d.fallback, n: d.n });
  };
}

export function StageBadge({ stage }: { stage?: string | null }) {
  const label = useStageLabel();
  if (!stage) return null;
  return <Badge tone="blue">{label(stage)}</Badge>;
}
