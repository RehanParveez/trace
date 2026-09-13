import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal,
} from "../../organizations/components/OrganizationUi";
import {useCreateClient, useUpdateClient,
} from "../hooks";
import { getApiErrorMessage } from "../../identity";
import type { Client } from "../types/project.types";
import { useTranslation } from "react-i18next";

interface ClientFormProps {
  client?: Client;
  onClose: () => void;
}

export function ClientForm({
  client,
  onClose,
}: ClientFormProps) {
  const { t } = useTranslation();
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
            setError(getApiErrorMessage(mutationError, t("clients.form.saveError")))
        },
      );

      return;
    }

    createClient.mutate(payload, {
      onSuccess: onClose,
      onError: (mutationError) =>
        setError(getApiErrorMessage(mutationError, t("clients.form.createError")))
    });
  }

  return (
   <Modal
    title={editing ? t("clients.form.editTitle") : t("clients.form.addTitle")}
    description={t("clients.form.description")}
    onClose={onClose}
    wide
  >
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("clients.form.name")}>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            className={inputClass}
          />
        </Field>

        <Field label={t("clients.form.contactName")}>
          <input
            value={contactName}
            onChange={(event) => setContactName(event.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label={t("clients.form.email")}>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label={t("clients.form.phone")}>
          <input
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className={inputClass}
          />
        </Field>
      </div>

      <Field label={t("clients.form.address")}>
        <input
          value={address}
          onChange={(event) => setAddress(event.target.value)}
          className={inputClass}
        />
      </Field>

      <Field label={t("clients.form.notes")}>
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
          {t("common.cancel")}
        </Button>

        <Button type="submit" variant="primary" disabled={isSubmitting || !name.trim()}>
          {isSubmitting
            ? t("common.saving")
            : editing
              ? t("common.saveChanges")
              : t("clients.form.addButton")}
        </Button>
      </div>
    </form>
  </Modal>
);
}