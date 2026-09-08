import type { Member } from "../types/organization.types";
import { EmptyState, Panel, PanelHeader, TableShell } from "./OrganizationUi";
import { MemberRow } from "./MemberRow";

interface MemberTableProps {
  members: Member[];
  canManage?: boolean;
  currentUserId?: string;
  onRoleChange?: (member: Member) => void;
  onStatusChange?: (member: Member) => void;
  onView?: (member: Member) => void;
}

export function MemberTable(props: MemberTableProps) {
  const { members } = props;

  return (
    <Panel>
      <PanelHeader
        eyebrow="WORKSPACE ACCESS"
        title="Members"
        description="Everyone with access to this organization's projects and data."
        action={
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">
            {members.length}
          </span>
        }
      />

      {members.length === 0 ? (
        <EmptyState
          icon="users"
          title="No members yet"
          description="Invite your team to give them access to projects, drawings and site data. Members appear here as soon as they accept an invitation."
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Member</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last login</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {members.map((member) => (
                <MemberRow key={member.id} {...props} member={member} />
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}
