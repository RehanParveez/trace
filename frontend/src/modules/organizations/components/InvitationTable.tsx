import type {Invitation,
} from "../types/organization.types";
import {formatDate, getInvitationStatus, getInvitationStatusTone,
} from "../utils/organization.utils";
import {Badge, Button, EmptyState, Icon, TableShell,
} from "./OrganizationUi";

interface InvitationTableProps {
  invitations: Invitation[];
  canManage?: boolean;
  onRevoke?: (
    invitation: Invitation,
  ) => void;
}

export function InvitationTable({
  invitations,
  canManage = false,
  onRevoke,
}: InvitationTableProps) {
  if (invitations.length === 0) {
    return (
      <EmptyState
        icon="mail"
        title="No invitations"
        description="There are no pending or historical organization invitations to show."
      />
    );
  }

  return (
    <TableShell>
      <table className="w-full min-w-[760px] text-left">
        <thead className="bg-[#f5efe3]">
          <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
            <th className="px-4 py-3">
              Invitee
            </th>

            <th className="px-4 py-3">
              Role ID
            </th>

            <th className="px-4 py-3">
              Status
            </th>

            <th className="px-4 py-3">
              Expires
            </th>

            <th className="px-4 py-3 text-right">
              Actions
            </th>
          </tr>
        </thead>

        <tbody>
          {invitations.map(
            (invitation) => {
              const status =
                getInvitationStatus(
                  invitation,
                );

              return (
                <tr
                  key={invitation.id}
                  className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]"
                >
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[#efe6d3] text-[#6b6152]">
                        <Icon
                          name="mail"
                          size={12}
                        />
                      </div>

                      <span className="text-[12px] font-semibold text-[#191410]">
                        {
                          invitation.email
                        }
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-3.5 font-mono text-[10px] text-[#6b6152]">
                    {
                      invitation.role_id
                    }
                  </td>

                  <td className="px-4 py-3.5">
                    <Badge
                      tone={getInvitationStatusTone(
                        status,
                      )}
                    >
                      {status}
                    </Badge>
                  </td>

                  <td className="px-4 py-3.5 text-[11px] text-[#6b6152]">
                    {formatDate(
                      invitation.expires_at,
                    )}
                  </td>

                  <td className="px-4 py-3.5 text-right">
                    {canManage &&
                    status ===
                      "pending" ? (
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() =>
                          onRevoke?.(
                            invitation,
                          )
                        }
                      >
                        Revoke
                      </Button>
                    ) : (
                      <span className="text-[10px] text-[#a2957c]">
                        —
                      </span>
                    )}
                  </td>
                </tr>
              );
            },
          )}
        </tbody>
      </table>
    </TableShell>
  );
}