import { useState } from "react";
import { Badge, Button, Icon, Panel, Modal, PanelHeader } from "../../organizations/components/OrganizationUi";
import { useChannel, useDisconnectChannel } from "../hooks";
import { ChannelConnectDialog } from "./ChannelConnectDialog";

interface ChannelStatusCardProps {
  canManage: boolean;
}

export function ChannelStatusCard({ canManage }: ChannelStatusCardProps) {
  const channelQuery = useChannel();
  const disconnect = useDisconnectChannel();
  const [connecting, setConnecting] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);

  const channel = channelQuery.data;

  return (
    <>
      <Panel>
        <PanelHeader
          eyebrow="MESSAGING CHANNEL"
          title="WhatsApp connection"
          description="Site engineers send progress photos to this number; Trace tags and files them automatically."
          action={channel ? <Badge tone={channel.is_active ? "green" : "slate"}>{channel.is_active ? "Connected" : "Disconnected"}</Badge> : null}
        />

        <div className="p-5">
          {channelQuery.isLoading ? (
            <div className="text-[11px] text-[#6b6152]">Checking connection…</div>
          ) : !channel ? (
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-[#efe6d3] text-[#6b6152]">
                  <Icon name="mail" size={16} />
                </div>
                <div>
                  <div className="text-[12.5px] font-semibold text-[#191410]">No WhatsApp number connected</div>
                  <div className="mt-0.5 text-[11px] text-[#6b6152]">Connect a Business number to start receiving site photos.</div>
                </div>
              </div>
              {canManage ? <Button variant="primary" onClick={() => setConnecting(true)}>Connect number</Button> : null}
            </div>
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-[13px] font-semibold text-[#191410]">{channel.display_phone_number ?? channel.phone_number_id}</div>
                <div className="mt-1 font-mono text-[10.5px] text-[#a2957c]">Phone number ID: {channel.phone_number_id}</div>
              </div>
              {canManage ? (
                <Button variant="danger" onClick={() => setConfirmingDisconnect(true)}>Disconnect</Button>
              ) : null}
            </div>
          )}
        </div>

        {!canManage ? (
          <div className="border-t border-[#e1d5bc] bg-[#f5efe3] px-5 py-3 text-[11px] text-[#6b6152]">
            You can view the connection status, but only users with channel management permission can connect or disconnect it.
          </div>
        ) : null}
      </Panel>

      {connecting ? <ChannelConnectDialog onClose={() => setConnecting(false)} /> : null}

      {confirmingDisconnect ? (
        <Modal title="Disconnect WhatsApp number" description="Site engineers will no longer be able to send photos to this number through Trace." onClose={() => setConfirmingDisconnect(false)}>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmingDisconnect(false)}>Cancel</Button>
            <Button
              variant="danger"
              disabled={disconnect.isPending}
              onClick={() => disconnect.mutate(undefined, { onSuccess: () => setConfirmingDisconnect(false) })}
            >
              {disconnect.isPending ? "Disconnecting…" : "Disconnect"}
            </Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}