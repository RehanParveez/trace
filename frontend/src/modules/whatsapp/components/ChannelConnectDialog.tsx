import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal } from "../../organizations/components/OrganizationUi";
import { useConnectChannel } from "../hooks";

interface ChannelConnectDialogProps {
  onClose: () => void;
}

export function ChannelConnectDialog({ onClose }: ChannelConnectDialogProps) {
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
      { onSuccess: onClose, onError: () => setError("Couldn't connect this number — it may already be connected elsewhere.") },
    );
  }

  return (
    <Modal title="Connect WhatsApp Business number" description="Connect this organization's WhatsApp Business Cloud API credentials." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Phone number ID" hint="From your Meta WhatsApp Business Platform app.">
          <input className={inputClass} required value={phoneNumberId} onChange={(e) => setPhoneNumberId(e.target.value)} />
        </Field>
        <Field label="Business account ID">
          <input className={inputClass} required value={businessAccountId} onChange={(e) => setBusinessAccountId(e.target.value)} />
        </Field>
        <Field label="Access token" hint="Stored securely and used only to send/receive messages on this number.">
          <input className={inputClass} required type="password" value={accessToken} onChange={(e) => setAccessToken(e.target.value)} />
        </Field>
        <Field label="Display phone number" hint="Optional — shown in the UI, e.g. +92 300 1234567">
          <input className={inputClass} value={displayPhoneNumber} onChange={(e) => setDisplayPhoneNumber(e.target.value)} />
        </Field>

        {error ? <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={connect.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={connect.isPending}>
            {connect.isPending ? "Connecting…" : "Connect number"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}