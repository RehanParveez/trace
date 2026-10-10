import { useTranslation } from "react-i18next";
import { ErrorState, PageHeader } from "../../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../../identity";
import { CalcUsagePanel } from "../components/CalcUsagePanel";
import { OrgCalcMetricsPanel } from "../components/OrgCalcMetricsPanel";
import { SCALE_PERMISSIONS } from "../permissions";

export function CalculationInsightsPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const allowed = permissions.includes(SCALE_PERMISSIONS.CALC_RUN);

  if (!allowed && permissions.length > 0) {
    return (
      <ErrorState
        title={t("scale.page.unavailable", "Calculation overview unavailable")}
        description={t("scale.page.noPermission", "You don't have permission to view this.")}
      />
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={t("scale.page.eyebrow", "CALCULATION")}
        title={t("scale.page.title", "Calculation overview")}
        description={t(
          "scale.page.description",
          "Your plan's calculation allowance, how many runs are going now, and how runs have performed across all projects.",
        )}
      />
      <CalcUsagePanel />
      <OrgCalcMetricsPanel />
    </div>
  );
}