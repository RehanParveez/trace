import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { SitePhotoGallery } from "../components/SitePhotoGallery";

export function SitePhotosPage() {
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.SITE_PHOTO_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title="Site photos" description="Photos sent to the organization's WhatsApp number, filed and searchable by project, date and tag." />
      <SitePhotoGallery canManage={canManage} />
    </div>
  );
}