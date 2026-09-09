import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal,
} from "../../organizations/components/OrganizationUi";
import {useCreateClient, useUpdateClient,
} from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { Client } from "../types/project.types";

interface ClientFormProps {
  client?: Client;
  onClose: () => void;
}

export function ClientForm({
  client,
  onClose,
}: ClientFormProps) {
  const createClient = useCreateClient();
  const updateClient = useUpdateClient();

  const editing = Boolean(client);

  const [name, setName] = useState(client?.name ?? "");
  const [contactName, setContactName] = useState(client?.contact_name ?? "");
  const [email, setEmail] = useState(client?.email ?? "");
  const [phone, setPhone] = useState(client?.phone ?? "");
  const [address, setAddress] = useState(client?.address ?? "");
  const [notes, setNotes] = useState(client?.notes ?? "");
  const [error, setError] = useState<string | null>(null);

  const isSubmitting = createClient.isPending || updateClient.isPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const payload = {
      name: name.trim(),
      contact_name: contactName.trim() || null,
      email: email.trim() || null,
      phone: phone.trim() || null,
      address: address.trim() || null,
      notes: notes.trim() || null,
    };

    if (editing && client) {
      updateClient.mutate(
        { clientId: client.id, payload },
        {
          onSuccess: onClose,
          onError: (mutationError) =>
            setError(getApiErrorMessage(mutationError, "Couldn't save this client. Please try again.")),
        },
      );

      return;
    }

    createClient.mutate(payload, {
      onSuccess: onClose,
      onError: (mutationError) =>
        setError(getApiErrorMessage(mutationError, "Couldn't create this client. It may already exist.")),
    });
  }

  return (
    <Modal
      title={editing ? "Edit client" : "Add client"}
      description="Client directory entry that can be linked to any project in this organization."
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Client name">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              className={inputClass}
            />
          </Field>

          <Field label="Contact name">
            <input
              value={contactName}
              onChange={(event) => setContactName(event.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Email">
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Phone">
            <input
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              className={inputClass}
            />
          </Field>
        </div>

        <Field label="Address">
          <input
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="Notes">
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={4}
            className={`${inputClass} resize-y`}
          />
        </Field>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>

          <Button type="submit" variant="primary" disabled={isSubmitting || !name.trim()}>
            {isSubmitting ? "Saving…" : editing ? "Save changes" : "Add client"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}