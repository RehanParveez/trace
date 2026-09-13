import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { MaterialLibraryPanel } from "../components/MaterialLibraryPanel";
import { useTranslation } from "react-i18next";

export function MaterialLibraryPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.MATERIAL_LIBRARY_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title={t("materials.page.title")} description={t("materials.page.description")} />
      <MaterialLibraryPanel canManage={canManage} />
    </div>
  );
}