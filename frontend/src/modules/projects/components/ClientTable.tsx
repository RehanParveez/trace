import { useState } from "react";
import {Button, Panel, PanelHeader
} from "../../organizations/components/OrganizationUi";
import {useDeleteClient,
} from "../hooks";
import type {Client,
} from "../types/project.types";
import { ClientForm } from "./ClientForm";

interface ClientTableProps {
  clients: Client[];
  canUpdate: boolean;
  canDelete: boolean;
}

export function ClientTable({
  clients,
  canUpdate,
  canDelete,
}: ClientTableProps) {
  const [formOpen, setFormOpen] =
    useState(false);

  const [editingClient, setEditingClient] =
    useState<Client | undefined>();

  const deleteClient =
    useDeleteClient();

  return (
    <>
      <Panel className="overflow-hidden">
        <PanelHeader
          eyebrow="CLIENT DIRECTORY"
          title="Clients"
          description="Client records that can be linked to any project in this organization."
          action={
            canUpdate ? (
              <Button
                variant="primary"
                onClick={() => {
                  setEditingClient(undefined);
                  setFormOpen(true);
                }}
              >
                Add client
              </Button>
            ) : undefined
          }
        />

        {clients.length === 0 ? (
          <div className="p-6 text-[12px] text-[var(--color-text-secondary)]">
            No clients have been created yet.
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {clients.map((client) => (
              <div
                key={client.id}
                className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="text-[14px] font-semibold text-[var(--color-text-primary)]">
                    {client.name}
                  </div>

                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-[var(--color-text-secondary)]">
                    {client.contact_name ? (
                      <span>
                        {client.contact_name}
                      </span>
                    ) : null}

                    {client.email ? (
                      <span>
                        {client.email}
                      </span>
                    ) : null}

                    {client.phone ? (
                      <span>
                        {client.phone}
                      </span>
                    ) : null}
                  </div>
                </div>

                {canUpdate ||
                canDelete ? (
                  <div className="flex gap-2">
                    {canUpdate ? (
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setEditingClient(
                            client,
                          );
                          setFormOpen(true);
                        }}
                      >
                        Edit
                      </Button>
                    ) : null}

                    {canDelete ? (
                      <Button
                        variant="ghost"
                        disabled={
                          deleteClient.isPending
                        }
                        onClick={() => {
                          if (
                            !window.confirm(
                              `Delete "${client.name}"?`,
                            )
                          ) {
                            return;
                          }

                          deleteClient.mutate(
                            client.id,
                          );
                        }}
                      >
                        Delete
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Panel>

      {formOpen ? (
        <ClientForm
          client={editingClient}
          onClose={() =>
            setFormOpen(false)
          }
        />
      ) : null}
    </>
  );
}