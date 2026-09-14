import { useState } from "react";
import axios from "axios";
import {Badge, Button, ErrorState, Icon, LoadingState, Modal, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useChannel, useDisconnectChannel } from "../hooks";
import { ChannelConnectDialog } from "./ChannelConnectDialog";
import { useTranslation } from "react-i18next";

interface ChannelStatusCardProps {
  canManage: boolean;
}

export function ChannelStatusCard({ canManage }: ChannelStatusCardProps) {
  const { t } = useTranslation();
  const channelQuery = useChannel();
  const disconnect = useDisconnectChannel();
  const { showToast } = useToast();
  const [connecting, setConnecting] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);
  const [disconnectError, setDisconnectError] = useState<string | null>(null);

  const channel = channelQuery.data;
  const channelNotFound =
    axios.isAxiosError(channelQuery.error) &&
    channelQuery.error.response?.status === 404;

  return (
    <>
      <Panel>
        <PanelHeader
          eyebrow={t("whatsapp.status.eyebrow")}
          title={t("whatsapp.status.title")}
          description={t("whatsapp.status.description")}
          action={
            channel ? (
              <Badge tone={channel.is_active ? "green" : "slate"}>
                {channel.is_active ? t("whatsapp.status.connected") : t("whatsapp.status.disconnected")}
              </Badge>
            ) : null
          }
        />

        <div className="p-5">
          {channelQuery.isLoading ? (
            <LoadingState label={t("whatsapp.status.checking")} />
          ) : channelQuery.isError && !channelNotFound ? (
            <ErrorState
              title={t("whatsapp.status.checkError")}
              onRetry={() => void channelQuery.refetch()}
            />
          ) : !channel || !channel.is_active ? (
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]">
                  <Icon name="mail" size={16} />
                </div>
                <div>
                  <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">
                    {t("whatsapp.status.noNumber")}
                  </div>
                  <div className="mt-0.5 text-[12px] text-[var(--color-text-secondary)]">
                    {t("whatsapp.status.noNumberDesc")}
                  </div>
                </div>
              </div>
              {canManage ? (
                <Button variant="primary" onClick={() => setConnecting(true)}>
                  {t("whatsapp.status.connect")}
                </Button>
              ) : null}
            </div>
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-[14.5px] font-semibold text-[var(--color-text-primary)]">
                  {channel.display_phone_number ?? channel.phone_number_id}
                </div>
                <div className="mt-1 font-mono text-[12px] text-[var(--color-text-muted)]">
                  Phone number ID: {channel.phone_number_id}
                </div>
              </div>
              {canManage ? (
                <Button
                  variant="danger"
                  onClick={() => {
                    setDisconnectError(null);
                    setConfirmingDisconnect(true);
                  }}
                >
                  Disconnect
                </Button>
              ) : null}
            </div>
          )}
        </div>

        {!canManage ? (
          <div className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-3 text-[12px] text-[var(--color-text-secondary)]">
            {t("whatsapp.status.viewOnly")}
          </div>
        ) : null}
      </Panel>

      {connecting ? (
        <ChannelConnectDialog onClose={() => setConnecting(false)} />
      ) : null}

      {confirmingDisconnect ? (
        <Modal
          title={t("whatsapp.disconnect.title")}
          description={t("whatsapp.disconnect.description")}
          onClose={() => setConfirmingDisconnect(false)}
        >
          <div className="space-y-3">
            {disconnectError ? (
              <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
                {disconnectError}
              </div>
            ) : null}
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setConfirmingDisconnect(false)}
              >
                {t("common.cancel")}
              </Button>
              <Button
                variant="danger"
                disabled={disconnect.isPending}
                onClick={() =>
                  disconnect.mutate(undefined, {
                    onSuccess: () => {
                      setConfirmingDisconnect(false);
                      showToast({
                        tone: "success",
                        title: t("whatsapp.disconnect.successToast"),
                      });
                    },
                    onError: (error) =>
                      setDisconnectError(
                        getApiErrorMessage(
                          error,
                          t("whatsapp.disconnect.error"),
                        ),
                      ),
                  })
                }
              >
                {disconnect.isPending ? t("whatsapp.disconnect.disconnecting") : t("whatsapp.status.disconnect")}
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}