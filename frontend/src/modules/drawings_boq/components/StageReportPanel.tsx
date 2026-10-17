import { EmptyState, ErrorState, LoadingState, Panel, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useTranslation } from "react-i18next";
import { useBOQStageReport } from "../hooks";
import { StageReportView } from "./StageReportView";

export function StageReportPanel({ versionId }: { versionId: string }) {
  const { t } = useTranslation();
  const q = useBOQStageReport(versionId);
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.stageReport.eyebrow", "BY STAGE AND TRADE")}
        title={t("boq.stageReport.title", "Quantities by stage and trade")}
        description={t(
          "boq.stageReport.description",
          "The bill in the order the work is done. Each quantity shows how far it could be out, from how its inputs were found on the drawing. Labour lines are left out.",
        )}
      />
      {q.isLoading ? (
        <LoadingState label={t("boq.stageReport.loading", "Loading the stage report…")} />
      ) : q.isError ? (
        <ErrorState title={t("boq.stageReport.loadError", "The stage report could not be loaded.")} onRetry={() => void q.refetch()} />
      ) : !q.data ? (
        <EmptyState icon="building" title={t("boq.stageReport.empty", "There are no quantities to report by stage yet.")} description="" />
      ) : (
        <StageReportView report={q.data} />
      )}
    </Panel>
  );
}
