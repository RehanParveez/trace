import type { Member } from "../types/organization.types";
import { EmptyState, Panel, PanelHeader, TableShell } from "./OrganizationUi";
import { MemberRow } from "./MemberRow";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  return (
    <Panel>
      <PanelHeader
       eyebrow={t("members.tableEyebrow")}
       title={t("members.tableTitle")}
       description={t("members.tableDesc")}
        action={
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">
            {members.length}
          </span>
        }
      />

      {members.length === 0 ? (
        <EmptyState
         icon="users"
         title={t("members.emptyTitle")}
         description={t("members.emptyDesc")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("members.colMember")}</th>
                <th className="px-4 py-3">{t("members.colRole")}</th>
                <th className="px-4 py-3">{t("members.colStatus")}</th>
                <th className="px-4 py-3">{t("members.colLastLogin")}</th>
                <th className="px-4 py-3 text-right">{t("members.colActions")}</th>
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
