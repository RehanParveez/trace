import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { SitePhotoGallery } from "../components/SitePhotoGallery";
import { useTranslation } from "react-i18next";

export function SitePhotosPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.SITE_PHOTO_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title={t("whatsapp.gallery.pageTitle")} description={t("whatsapp.gallery.pageDescription")} />
      <SitePhotoGallery canManage={canManage} />
    </div>
  );
}