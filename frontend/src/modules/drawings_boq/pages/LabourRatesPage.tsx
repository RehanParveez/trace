import { PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { DRAWINGS_BOQ_PERMISSIONS } from "../permissions";
import { LabourRatesPanel } from "../components/LabourRatesPanel";

export function LabourRatesPage() {
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(DRAWINGS_BOQ_PERMISSIONS.LABOUR_RATE_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title="Labour rates" description="Per-trade labour rates used to auto-generate labour costs on any project's BOQ." />
      <LabourRatesPanel canManage={canManage} />
    </div>
  );
}