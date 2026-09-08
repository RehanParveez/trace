import type { Invitation, Role } from "../types/organization.types";
import {formatDate, getInvitationStatus, getInvitationStatusTone,
} from "../utils/organization.utils";
import {Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell,
} from "./OrganizationUi";

interface InvitationTableProps {
  invitations: Invitation[];
  roles?: Role[];
  canManage?: boolean;
  onRevoke?: (invitation: Invitation) => void;
}

export function InvitationTable({
  invitations,
  roles = [],
  canManage = false,
  onRevoke,
}: InvitationTableProps) {
  function roleLabel(roleId: string): string {
    return roles.find((role) => role.id === roleId)?.name ?? roleId;
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="ACCESS HISTORY"
        title="Invitations"
        description="Pending, accepted and expired invitations for this organization."
        action={
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">
            {invitations.length}
          </span>
        }
      />

      {invitations.length === 0 ? (
        <EmptyState
          icon="mail"
          title="No invitations"
          description="There are no pending or historical organization invitations to show."
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Invitee</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Expires</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {invitations.map((invitation) => {
                const status = getInvitationStatus(invitation);

                return (
                  <tr
                    key={invitation.id}
                    className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]"
                  >
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]">
                          <Icon name="mail" size={12} />
                        </div>

                        <span className="truncate text-[13px] font-semibold text-[var(--color-text-primary)]">
                          {invitation.email}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-3.5 text-[12.5px] font-semibold text-[var(--color-text-primary)]">
                      {roleLabel(invitation.role_id)}
                    </td>

                    <td className="px-4 py-3.5">
                      <Badge tone={getInvitationStatusTone(status)}>
                        {status}
                      </Badge>
                    </td>

                    <td className="px-4 py-3.5 text-[12px] text-[var(--color-text-secondary)]">
                      {formatDate(invitation.expires_at)}
                    </td>

                    <td className="px-4 py-3.5 text-right">
                      {canManage && status === "pending" ? (
                        <Button
                          type="button"
                          variant="danger"
                          size="sm"
                          onClick={() => onRevoke?.(invitation)}
                        >
                          Revoke
                        </Button>
                      ) : (
                        <span className="text-[11px] text-[var(--color-text-muted)]">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
