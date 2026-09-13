import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { LabourRatesPanel } from "../components/LabourRatesPanel";
import { useTranslation } from "react-i18next";

export function LabourRatesPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.LABOUR_RATE_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title={t("labour.page.title")} description={t("labour.page.description")} />
      <LabourRatesPanel canManage={canManage} />
    </div>
  );
}