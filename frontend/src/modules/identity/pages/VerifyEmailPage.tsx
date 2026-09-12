import {useEffect, useState, useRef
} from "react";
import {Link, useSearchParams,
} from "react-router-dom";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { useResendVerification, useVerifyEmail } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";
import { useTranslation } from "react-i18next";

export function VerifyEmailPage() {
  const [params] =
    useSearchParams();

  const autoVerificationAttempted = 
    useRef(false);

  const { t } = useTranslation();

  const verify =
    useVerifyEmail();

  const resend =
    useResendVerification();

  const [resendEmail, setResendEmail] =
    useState("");

  const initialToken =
    params.get("token") ?? "";

  const [token, setToken] =
    useState(initialToken);

  useEffect(() => {
  if (!initialToken || autoVerificationAttempted.current) {
    return;
  }

  autoVerificationAttempted.current = true;
  verify.mutate({ token: initialToken });
}, [initialToken, verify]);

  function submit(
    event: React.FormEvent,
  ) {
    event.preventDefault();

    verify.mutate({
      token: token.trim(),
    });
  }

  return (
    <AuthShell
      eyebrow={t("auth.verify.eyebrow")}
      title={
        <>
          {t("auth.verify.title").split(" ").slice(0, 2).join(" ")}
          <br />
          <em className="text-[var(--color-trace-gold-dark)]">
            {t("auth.verify.title").split(" ").slice(2).join(" ")}
          </em>
        </>
      }
      description={t("auth.verify.description")}
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          <Link
            to="/login"
            className="font-bold text-[var(--color-trace-gold-dark)] hover:underline"
          >
            {t("auth.verify.continue")}
          </Link>
        </p>
      }
    >
      {verify.isSuccess ? (
        <div className="space-y-4">
          <AuthNotice tone="success">
            {t("auth.verify.success")}
          </AuthNotice>

          <Link
            to="/login"
            className="flex h-12 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-trace-gold)] text-[14px] font-semibold text-[var(--color-trace-navy)] transition hover:bg-[var(--color-trace-gold-dark)]"
          >
            {t("auth.verify.continue")}
          </Link>
        </div>
      ) : (
        <form
          onSubmit={submit}
          className="space-y-4"
        >
          {verify.isError && (
            <AuthNotice tone="error">
              {getApiErrorMessage(
                verify.error,
                t("auth.verify.error"),
              )}
            </AuthNotice>
          )}

          {verify.isError && (
            <div className="space-y-2 rounded-[9px] border border-[#E1D5BC] bg-[#F8F3E9] p-3.5">
              {resend.isSuccess ? (
                <AuthNotice tone="success">
                  {t("auth.verify.resendSuccess")}
                </AuthNotice>
              ) : (
                <>
                  <p className="text-[11.5px] text-[#6B6152]">
                    {t("auth.verify.expired")}
                  </p>

                  <div className="flex gap-2">
                    <input
                      type="email"
                      value={resendEmail}
                      onChange={(event) => setResendEmail(event.target.value)}
                      placeholder="you@company.com"
                      className="h-10 flex-1 rounded-[8px] border border-[#E1D5BC] bg-white px-3 text-[12px] outline-none focus:border-[#D9A441]"
                    />

                    <button
                      type="button"
                      disabled={resend.isPending || !resendEmail.trim()}
                      onClick={() =>
                        resend.mutate({ email: resendEmail.trim().toLowerCase() })
                      }
                      className="h-10 shrink-0 rounded-[8px] bg-[#0D1424] px-3.5 text-[11.5px] font-bold text-white disabled:opacity-50"
                    >
                      {resend.isPending ? t("auth.verify.sending") : t("auth.verify.resend")}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          <label className="block">
            <span className="mb-2 block text-[12px] font-semibold text-[#332A21]">
              {t("auth.verify.token")}
            </span>

            <textarea
              value={token}
              onChange={(event) =>
                setToken(
                  event.target.value,
                )
              }
              rows={4}
              className="
                w-full resize-none
                rounded-[9px]
                border border-[#E1D5BC]
                bg-[#FBF8F2]
                p-3.5 text-[12px]
                outline-none
                focus:border-[#D9A441]
                focus:ring-4
                focus:ring-[#D9A441]/10
              "
            />
          </label>

          <button
            type="submit"
            disabled={
              verify.isPending ||
              !token.trim()
            }
            className="h-12 w-full rounded-[var(--radius-sm)] bg-[var(--color-trace-gold)] text-[14px] font-semibold text-[var(--color-trace-navy)] transition hover:bg-[var(--color-trace-gold-dark)] disabled:cursor-not-allowed disabled:opacity-50">
            {verify.isPending
              ? t("auth.verify.submitting")
              : t("auth.verify.submit")}
          </button>
        </form>
      )}
    </AuthShell>
  );
}