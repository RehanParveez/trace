import type {Member,
} from "../types/organization.types";
import {EmptyState, TableShell,
} from "./OrganizationUi";
import {MemberRow,
} from "./MemberRow";

interface MemberTableProps {
  members: Member[];
  canManage?: boolean;
  onRoleChange?: (
    member: Member,
  ) => void;
  onStatusChange?: (
    member: Member,
  ) => void;
  onView?: (
    member: Member,
  ) => void;
}

export function MemberTable(
  props: MemberTableProps,
) {
  const {
    members,
  } = props;

  if (members.length === 0) {
    return (
      <EmptyState
        icon="users"
        title="No members yet"
        description="Your organization has no member records matching the current view."
      />
    );
  }

  return (
    <TableShell>
      <table className="w-full min-w-[760px] text-left">
        <thead className="bg-[#f5efe3]">
          <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
            <th className="px-4 py-3">
              Member
            </th>

            <th className="px-4 py-3">
              Role
            </th>

            <th className="px-4 py-3">
              Status
            </th>

            <th className="px-4 py-3">
              Last login
            </th>

            <th className="px-4 py-3 text-right">
              Actions
            </th>
          </tr>
        </thead>

        <tbody>
          {members.map(
            (member) => (
              <MemberRow
                key={member.id}
                {...props}
                member={member}
              />
            ),
          )}
        </tbody>
      </table>
    </TableShell>
  );
}