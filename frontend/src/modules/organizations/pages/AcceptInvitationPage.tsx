import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAcceptInvitation } from "../hooks";
import {BrandMark, Button, Field, Icon, inputClass, PageHeader, Panel, PanelHeader,
} from "../components/OrganizationUi";
import { useTranslation } from "react-i18next";

function BrandBar() {
  return (
    <div className="mb-8 flex items-center gap-2.5">
      <BrandMark />

      <div>
        <div className="font-[Archivo] text-[15px] font-semibold tracking-[-0.03em] text-[#191410]">
          Trace
        </div>

        <div className="text-[8px] font-medium uppercase tracking-[0.2em] text-[#a2957c]">
          Construction Intelligence
        </div>
      </div>
    </div>
  );
}

export function AcceptInvitationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const { t } = useTranslation();

  const acceptInvitation = useAcceptInvitation();

  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [result, setResult] = useState<Awaited<
    ReturnType<typeof acceptInvitation.mutateAsync>
  > | null>(null);

  useEffect(() => {
    const queryToken = searchParams.get("token");

    if (queryToken) {
      setToken(queryToken);
    }
  }, [searchParams]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const response = await acceptInvitation.mutateAsync({
      token: token.trim(),
    });

    setResult(response);
  }

  if (result) {
    return (
      <div className="min-h-screen bg-[var(--color-workspace)] px-4 py-10">
        <div className="mx-auto max-w-xl">
          <BrandBar />

          <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-[10px]bg-[var(--color-success-bg)] text-[var(--color-success)]">
            <Icon name="check" size={20} />
          </div>

          <h1 className="font-['Fraunces',serif] text-[26px] font-semibold italic tracking-[-0.01em] text-[#191410]">
            {t("accept.successTitle")}
          </h1>

          <p className="mt-2 max-w-md text-[13px] leading-5 text-[var(--color-text-secondary)]">
            {result.message}
          </p>

          <div className="mt-6">
            <Panel>
              <PanelHeader
                eyebrow={t("accept.workspaceAccess")}
                title={t("accept.membershipCreated")}
              />

              <div className="grid gap-0 divide-y divide-[var(--color-border)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
                <div className="p-5">
                  <div className="text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                    {t("accept.organization")}
                  </div>

                  <div className="mt-1.5 text-[13px] font-semibold text-[var(--color-text-primary)]">
                    {result.organization_name}
                  </div>
                </div>

                <div className="p-5">
                  <div className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                    {t("accept.role")}
                  </div>

                  <div className="mt-1.5 text-[13px] font-semibold text-[var(--color-text-primary)]">
                    {result.role_name}
                  </div>
                </div>
              </div>

              <div className="border-t border-[var(--color-border)] p-5">
                <Button variant="primary" onClick={() => navigate("/app")}>
                  {t("accept.continue")}
                  <Icon name="arrow" size={13} />
                </Button>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5efe3] px-4 py-10">
      <div className="mx-auto max-w-xl">
        <BrandBar />

        <PageHeader
          eyebrow={t("accept.eyebrow")}
          title={t("accept.title")}
          description={t("accept.description")}
        />

        <Panel>
          <PanelHeader eyebrow={t("accept.secureAccess")} title={t("accept.tokenTitle")} />

          <form onSubmit={handleSubmit} className="space-y-4 p-5">
            <Field
              label={t("accept.tokenLabel")}
              hint={t("accept.tokenHint")}
            >
              <textarea
                value={token}
                onChange={(event) => setToken(event.target.value)}
                required
                rows={5}
                className={`${inputClass} resize-y font-mono text-[11px]`}
              />
            </Field>

            {acceptInvitation.isError ? (
              <div className="flex items-center gap-2 rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
                <Icon name="alert" size={13} className="shrink-0" />
                {t("accept.error")}
              </div>
            ) : null}

            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                disabled={acceptInvitation.isPending || !token.trim()}
              >
                <Icon name="check" size={13} />

                {acceptInvitation.isPending ? t("accept.accepting") : t("accept.submit")}
              </Button>
            </div>
          </form>
        </Panel>
      </div>
    </div>
  );
}
