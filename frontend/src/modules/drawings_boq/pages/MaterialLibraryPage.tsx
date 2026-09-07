import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { MaterialLibraryPanel } from "../components/MaterialLibraryPanel";

export function MaterialLibraryPage() {
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.MATERIAL_LIBRARY_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title="Material library" description="The organization-wide dictionary used to normalize messy material text extracted from drawings." />
      <MaterialLibraryPanel canManage={canManage} />
    </div>
  );
}