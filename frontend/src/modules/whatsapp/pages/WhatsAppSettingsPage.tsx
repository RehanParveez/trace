import { PageHeader } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { ChannelStatusCard } from "../components/ChannelStatusCard";

export function WhatsAppSettingsPage() {
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(IDENTITY_PERMISSIONS.WHATSAPP_CHANNEL_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title="WhatsApp connection" description="Connect the organization's WhatsApp Business number so site engineers can send progress photos directly to Trace." />
      <ChannelStatusCard canManage={canManage} />
    </div>
  );
}