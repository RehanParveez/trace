import { PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { DRAWINGS_BOQ_PERMISSIONS } from "../permissions";
import { MaterialLibraryPanel } from "../components/MaterialLibraryPanel";

export function MaterialLibraryPage() {
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(DRAWINGS_BOQ_PERMISSIONS.MATERIAL_LIBRARY_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title="Material library" description="The organization-wide dictionary used to normalize messy material text extracted from drawings." />
      <MaterialLibraryPanel canManage={canManage} />
    </div>
  );
}