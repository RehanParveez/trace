import { PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { WHATSAPP_PERMISSIONS } from "../permissions";
import { ChannelStatusCard } from "../components/ChannelStatusCard";

export function WhatsAppSettingsPage() {
  const permissions = usePermissionKeys();
  const canManage = permissions.includes(WHATSAPP_PERMISSIONS.WHATSAPP_CHANNEL_MANAGE);

  return (
    <div className="space-y-7">
      <PageHeader title="WhatsApp connection" description="Connect the organization's WhatsApp Business number so site engineers can send progress photos directly to Trace." />
      <ChannelStatusCard canManage={canManage} />
    </div>
  );
}