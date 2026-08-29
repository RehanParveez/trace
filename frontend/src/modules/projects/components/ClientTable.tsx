import { useState } from "react";
import {Button, Panel,
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
        <div className="flex items-center justify-between border-b border-[#e1d5bc] p-5 sm:p-6">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
              CLIENT DIRECTORY
            </div>

            <div className="mt-1 font-[Archivo] text-[17px] font-bold text-[#191410]">
              Clients
            </div>
          </div>

          {canUpdate ? (
            <Button
              variant="primary"
              onClick={() => {
                setEditingClient(
                  undefined,
                );
                setFormOpen(true);
              }}
            >
              Add client
            </Button>
          ) : null}
        </div>

        {clients.length === 0 ? (
          <div className="p-6 text-[11px] text-[#756957]">
            No clients have been created yet.
          </div>
        ) : (
          <div className="divide-y divide-[#e1d5bc]">
            {clients.map((client) => (
              <div
                key={client.id}
                className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="text-[12px] font-semibold text-[#191410]">
                    {client.name}
                  </div>

                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[#756957]">
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