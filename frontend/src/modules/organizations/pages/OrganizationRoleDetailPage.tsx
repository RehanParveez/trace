import {useNavigate, useParams,
} from "react-router-dom";
import {useMember,
} from "../hooks";
import {Avatar, Badge, Button, ErrorState, Icon, LoadingState, PageHeader, Panel, PanelHeader,
} from "../components/OrganizationUi";
import {formatDateTime, getMemberFullName, getMemberInitials,
} from "../utils/organization.utils";

export function OrganizationMemberDetailPage() {
  const navigate =
    useNavigate();

  const {
    userId,
  } = useParams<{
    userId: string;
  }>();

  const memberQuery =
    useMember(userId);

  if (memberQuery.isLoading) {
    return (
      <LoadingState
        label="Loading member…"
      />
    );
  }

  if (
    memberQuery.isError ||
    !memberQuery.data
  ) {
    return (
      <ErrorState
        title="Member not found"
        description="The member record could not be loaded for this organization."
        onRetry={() =>
          void memberQuery.refetch()
        }
      />
    );
  }

  const member =
    memberQuery.data;

  return (
    <div>
      <PageHeader
        eyebrow="MEMBER DETAIL"
        title={getMemberFullName(
          member,
        )}
        description={
          member.email
        }
        actions={
          <Button
            variant="ghost"
            onClick={() =>
              navigate(
                "/app/organization/members",
              )
            }
          >
            <Icon
              name="arrow"
              size={13}
            />
            Back to members
          </Button>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <Panel>
          <PanelHeader
            eyebrow="IDENTITY & ACCESS"
            title="Member profile"
            description="The organization-level identity and access state returned by the API."
          />

          <div className="flex items-center gap-4 border-b border-[#e1d5bc] p-5">
            <Avatar
              initials={getMemberInitials(
                member,
              )}
              size="lg"
            />

            <div>
              <div className="font-[Archivo] text-[17px] font-bold text-[#191410]">
                {getMemberFullName(
                  member,
                )}
              </div>

              <div className="mt-1 text-[11px] text-[#6b6152]">
                {
                  member.email
                }
              </div>

              <div className="mt-2 flex flex-wrap gap-2">
                <Badge
                  tone={
                    member.is_active
                      ? "green"
                      : "slate"
                  }
                >
                  {member.is_active
                    ? "Active"
                    : "Inactive"}
                </Badge>

                <Badge
                  tone={
                    member.is_verified
                      ? "blue"
                      : "gold"
                  }
                >
                  {member.is_verified
                    ? "Verified"
                    : "Unverified"}
                </Badge>
              </div>
            </div>
          </div>

          <dl className="grid gap-0 divide-y divide-[#e1d5bc] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            {[
              [
                "Role",
                member.role.name,
              ],
              [
                "Role type",
                member.role
                  .is_system
                  ? "System role"
                  : "Custom role",
              ],
              [
                "Verification",
                member.is_verified
                  ? "Verified"
                  : "Unverified",
              ],
              [
                "Last login",
                formatDateTime(
                  member.last_login_at,
                ),
              ],
            ].map(
              ([label, value]) => (
                <div
                  key={label}
                  className="p-5"
                >
                  <dt className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                    {label}
                  </dt>

                  <dd className="mt-1.5 text-[12.5px] font-semibold text-[#191410]">
                    {value}
                  </dd>
                </div>
              ),
            )}
          </dl>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="ROLE BOUNDARY"
            title="Granted permissions"
          />

          <div className="space-y-2 p-5">
            {member.role
              .permissions.length ===
            0 ? (
              <div className="text-[11px] text-[#6b6152]">
                No permissions are attached to this role.
              </div>
            ) : (
              member.role.permissions.map(
                (permission) => (
                  <div
                    key={
                      permission.id
                    }
                    className="rounded-[8px] border border-[#e1d5bc] bg-white p-3"
                  >
                    <div className="break-all font-mono text-[10px] font-semibold text-[#332a21]">
                      {
                        permission.key
                      }
                    </div>

                    {permission.description ? (
                      <div className="mt-1 text-[10px] leading-4 text-[#6b6152]">
                        {
                          permission.description
                        }
                      </div>
                    ) : null}
                  </div>
                ),
              )
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}