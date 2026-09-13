import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { ChannelStatusCard } from "../components/ChannelStatusCard";
import { useTranslation } from "react-i18next";

export function WhatsAppSettingsPage() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.WHATSAPP_CHANNEL_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title={t("whatsapp.status.title")} description={t("whatsapp.status.pageDescription")} />
      <ChannelStatusCard canManage={canManage} />
    </div>
  );
}