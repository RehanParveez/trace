import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useConnectChannel } from "../hooks";
import { useTranslation } from "react-i18next";

interface ChannelConnectDialogProps {
  onClose: () => void;
}

export function ChannelConnectDialog({ onClose }: ChannelConnectDialogProps) {
  const { t } = useTranslation();
  const connect = useConnectChannel();
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [businessAccountId, setBusinessAccountId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [displayPhoneNumber, setDisplayPhoneNumber] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    connect.mutate(
  {
    phone_number_id: phoneNumberId.trim(),
    business_account_id: businessAccountId.trim(),
    access_token: accessToken.trim(),
    display_phone_number: displayPhoneNumber.trim() || null,
  },
  {
    onSuccess: onClose,
    onError: (mutationError) =>
      setError(getApiErrorMessage(mutationError, t("whatsapp.connect.error")))
  },
);
}

  return (
    <Modal title={t("whatsapp.connect.title")} description={t("whatsapp.connect.description")} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t("whatsapp.connect.phoneNumberId")} hint={t("whatsapp.connect.phoneNumberIdHint")}>
          <input className={inputClass} required value={phoneNumberId} onChange={(e) => setPhoneNumberId(e.target.value)} />
        </Field>
        <Field label={t("whatsapp.connect.businessAccountId")}>
          <input className={inputClass} required value={businessAccountId} onChange={(e) => setBusinessAccountId(e.target.value)} />
        </Field>
        <Field label={t("whatsapp.connect.accessToken")} hint={t("whatsapp.connect.accessTokenHint")}>
          <input className={inputClass} required type="password" value={accessToken} onChange={(e) => setAccessToken(e.target.value)} />
        </Field>
        <Field label={t("whatsapp.connect.displayPhone")} hint={t("whatsapp.connect.displayPhoneHint")}>
          <input className={inputClass} value={displayPhoneNumber} onChange={(e) => setDisplayPhoneNumber(e.target.value)} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={connect.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" disabled={connect.isPending}>
            {connect.isPending ? t("whatsapp.connect.connecting") : t("whatsapp.connect.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}