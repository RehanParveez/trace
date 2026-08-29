import { useState } from "react";
import type { FormEvent } from "react";
import {Button,
} from "../../organizations/components/OrganizationUi";
import {useCreateClient, useUpdateClient,
} from "../hooks";
import type {Client,
} from "../types/project.types";

interface ClientFormProps {
  client?: Client;
  onClose: () => void;
}

export function ClientForm({
  client,
  onClose,
}: ClientFormProps) {
  const createClient =
    useCreateClient();

  const updateClient =
    useUpdateClient();

  const editing = Boolean(client);

  const [name, setName] =
    useState(client?.name ?? "");

  const [contactName, setContactName] =
    useState(
      client?.contact_name ?? "",
    );

  const [email, setEmail] =
    useState(client?.email ?? "");

  const [phone, setPhone] =
    useState(client?.phone ?? "");

  const [address, setAddress] =
    useState(client?.address ?? "");

  const [notes, setNotes] =
    useState(client?.notes ?? "");

  const isSubmitting =
    createClient.isPending ||
    updateClient.isPending;

  function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const payload = {
      name: name.trim(),
      contact_name:
        contactName.trim() || null,
      email: email.trim() || null,
      phone: phone.trim() || null,
      address:
        address.trim() || null,
      notes: notes.trim() || null,
    };

    if (editing && client) {
      updateClient.mutate(
        {
          clientId: client.id,
          payload,
        },
        {
          onSuccess: onClose,
        },
      );

      return;
    }

    createClient.mutate(payload, {
      onSuccess: onClose,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#16283f]/45 p-4 backdrop-blur-[2px]">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[12px] border border-[#d9ceb9] bg-[#fbf8f2] shadow-[0_24px_70px_rgba(20,25,35,0.22)]">
        <div className="border-b border-[#e1d5bc] p-5">
          <div className="text-[9px] font-bold uppercase tracking-[0.14em] text-[#a2957c]">
            CLIENT DIRECTORY
          </div>

          <h2 className="mt-1 font-[Archivo] text-[21px] font-bold text-[#191410]">
            {editing
              ? "Edit client"
              : "Add client"}
          </h2>
        </div>

        <form
          onSubmit={submit}
          className="space-y-5 p-5"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Client name"
              value={name}
              onChange={setName}
              required
            />

            <Input
              label="Contact name"
              value={contactName}
              onChange={setContactName}
            />

            <Input
              label="Email"
              value={email}
              onChange={setEmail}
              type="email"
            />

            <Input
              label="Phone"
              value={phone}
              onChange={setPhone}
            />
          </div>

          <Input
            label="Address"
            value={address}
            onChange={setAddress}
          />

          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              Notes
            </span>

            <textarea
              value={notes}
              onChange={(event) =>
                setNotes(
                  event.target.value,
                )
              }
              rows={4}
              className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
            />
          </label>

          <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="primary"
              disabled={
                isSubmitting ||
                !name.trim()
              }
            >
              {isSubmitting
                ? "Saving..."
                : editing
                  ? "Save changes"
                  : "Add client"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface InputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: string;
}

function Input({
  label,
  value,
  onChange,
  required,
  type = "text",
}: InputProps) {
  return (
    <label className="block">
      <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
        {label}
        {required ? " *" : ""}
      </span>

      <input
        type={type}
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        required={required}
        className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
      />
    </label>
  );
}