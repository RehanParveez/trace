import { useNavigate, useParams } from "react-router-dom";
import { useMember } from "../hooks";
import {Avatar, Badge, Button, ErrorState, Icon, LoadingState, PageHeader, Panel, PanelHeader,
} from "../components/OrganizationUi";
import {formatDateTime, getMemberFullName, getMemberInitials, humanizePermission,
} from "../utils/organization.utils";
import { useTranslation } from "react-i18next";

export function OrganizationMemberDetailPage() {
  const navigate = useNavigate();
  const { userId } = useParams<{ userId: string }>();
  const { t } = useTranslation();
  const memberQuery = useMember(userId);

  if (memberQuery.isLoading) {
    return <LoadingState label={t("memberDetail.loading")} />;
  }

  if (memberQuery.isError || !memberQuery.data) {
    return (
      <ErrorState
        title={t("memberDetail.notFound")}
        description={t("memberDetail.notFoundDesc")}
        onRetry={() => void memberQuery.refetch()}
      />
    );
  }

  const member = memberQuery.data;

  const details: Array<[string, string]> = [
    [t("memberDetail.role"), member.role.name],
    [t("memberDetail.roleType"), member.role.is_system ? t("memberDetail.systemRole") : t("memberDetail.customRole")],
    [t("memberDetail.verification"), member.is_verified ? t("memberDetail.verified") : t("memberDetail.unverified")],
    [t("memberDetail.lastLogin"), formatDateTime(member.last_login_at)],
  ];

  return (
    <div>
      <PageHeader
        eyebrow={t("memberDetail.eyebrow")}
        title={getMemberFullName(member)}
        description={member.email}
        actions={
          <Button
            variant="ghost"
            onClick={() => navigate("/app/organization/members")}
          >
            <Icon name="arrow" size={13} />
            {t("memberDetail.back")}
          </Button>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <Panel>
          <PanelHeader
            eyebrow={t("memberDetail.identityAccess")}
            title={t("memberDetail.profile")}
            description={t("memberDetail.profileDesc")}
          />

          <div className="flex items-center gap-4 border-b border-[#e1d5bc] p-5">
            <Avatar initials={getMemberInitials(member)} size="lg" />

            <div>
              <div className="font-[Archivo] text-[17px] font-bold text-[#191410]">
                {getMemberFullName(member)}
              </div>

              <div className="mt-1 text-[11px] text-[#6b6152]">
                {member.email}
              </div>

              <div className="mt-2 flex flex-wrap gap-2">
                <Badge tone={member.is_active ? "green" : "slate"}>
                  member.is_active ? t("memberDetail.active") : t("memberDetail.inactive")
                </Badge>

                <Badge tone={member.is_verified ? "blue" : "gold"}>
                  {member.is_verified ? "Verified" : "Unverified"}
                </Badge>
              </div>
            </div>
          </div>

          <dl className="grid gap-0 divide-y divide-[var(--color-border)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            {details.map(([label, value]) => (
              <div key={label} className="p-5">
                <dt className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                  {label}
                </dt>

                <dd className="mt-1.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </Panel>

        <Panel>
          <PanelHeader eyebrow={t("memberDetail.roleBoundary")} title={t("memberDetail.grantedPermissions")} />

          <div className="space-y-2 p-5">
            {member.role.permissions.length === 0 ? (
              <div className="text-[12px] text-[var(--color-text-secondary)]">
                {t("memberDetail.noPermissions")}
              </div>
            ) : (
              member.role.permissions.map((permission) => {
                const { label } = humanizePermission(permission.key);

                return (
                  <div
                    key={permission.id}
                    className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3"
                  >
                    <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">
                      {label}
                    </div>

                    <div className="mt-0.5 break-all font-mono text-[10.5px] text-[var(--color-text-muted)]">
                      {permission.key}
                    </div>

                    {permission.description ? (
                      <div className="mt-1 text-[11.5px] leading-4 text-[var(--color-text-secondary)]">
                        {permission.description}
                      </div>
                    ) : null}
                  </div>
                );
              })
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
