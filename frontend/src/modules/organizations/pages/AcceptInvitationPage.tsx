import {useEffect, useState,
} from "react";
import type {FormEvent,
} from "react";
import {useNavigate, useSearchParams,
} from "react-router-dom";
import {useAcceptInvitation,
} from "../hooks";
import {Button, Field, Icon, inputClass, PageHeader, Panel, PanelHeader,
} from "../components/OrganizationUi";

export function AcceptInvitationPage() {
  const navigate =
    useNavigate();

  const [
    searchParams,
  ] = useSearchParams();

  const acceptInvitation =
    useAcceptInvitation();

  const [
    token,
    setToken,
  ] = useState(
    searchParams.get(
      "token",
    ) ?? "",
  );

  const [
    result,
    setResult,
  ] = useState<
    Awaited<
      ReturnType<
        typeof acceptInvitation.mutateAsync
      >
    > | null
  >(null);

  useEffect(() => {
    const queryToken =
      searchParams.get(
        "token",
      );

    if (queryToken) {
      setToken(queryToken);
    }
  }, [
    searchParams,
  ]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const response =
      await acceptInvitation.mutateAsync(
        {
          token:
            token.trim(),
        },
      );

    setResult(response);
  }

  if (result) {
    return (
      <div className="min-h-screen bg-[#f5efe3] px-4 py-10">
        <div className="mx-auto max-w-xl">
          <PageHeader
            eyebrow="INVITATION"
            title="Invitation accepted"
            description={
              result.message
            }
          />

          <Panel>
            <PanelHeader
              eyebrow="WORKSPACE ACCESS"
              title="Membership created"
            />

            <div className="grid gap-0 divide-y divide-[#e1d5bc] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
              <div className="p-5">
                <div className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                  Organization
                </div>

                <div className="mt-1.5 text-[13px] font-semibold text-[#191410]">
                  {
                    result.organization_name
                  }
                </div>
              </div>

              <div className="p-5">
                <div className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                  Role
                </div>

                <div className="mt-1.5 text-[13px] font-semibold text-[#191410]">
                  {
                    result.role_name
                  }
                </div>
              </div>
            </div>

            <div className="border-t border-[#e1d5bc] p-5">
              <Button
                variant="primary"
                onClick={() =>
                  navigate(
                    "/app",
                  )
                }
              >
                Continue to workspace

                <Icon
                  name="arrow"
                  size={13}
                />
              </Button>
            </div>
          </Panel>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5efe3] px-4 py-10">
      <div className="mx-auto max-w-xl">
        <PageHeader
          eyebrow="ACCESS INVITATION"
          title="Accept invitation"
          description="Enter the invitation token you received. The server remains authoritative for acceptance and role assignment."
        />

        <Panel>
          <PanelHeader
            eyebrow="SECURE ACCESS"
            title="Invitation token"
          />

          <form
            onSubmit={
              handleSubmit
            }
            className="space-y-4 p-5"
          >
            <Field
              label="Token"
              hint="Paste the complete invitation token exactly as received."
            >
              <textarea
                value={token}
                onChange={(event) =>
                  setToken(
                    event.target.value,
                  )
                }
                required
                rows={5}
                className={`${inputClass} resize-y font-mono text-[11px]`}
              />
            </Field>

            {acceptInvitation.isError ? (
              <div className="rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">
                Unable to accept this invitation. The token may be invalid, expired or already used.
              </div>
            ) : null}

            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                disabled={
                  acceptInvitation.isPending ||
                  !token.trim()
                }
              >
                <Icon
                  name="check"
                  size={13}
                />

                {acceptInvitation.isPending
                  ? "Accepting…"
                  : "Accept invitation"}
              </Button>
            </div>
          </form>
        </Panel>
      </div>
    </div>
  );
}