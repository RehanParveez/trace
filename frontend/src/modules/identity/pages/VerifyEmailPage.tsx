import {useEffect, useState,
} from "react";
import {Link, useSearchParams,
} from "react-router-dom";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { useResendVerification, useVerifyEmail } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";

export function VerifyEmailPage() {
  const [params] =
    useSearchParams();

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
    if (initialToken) {
      verify.mutate({
        token: initialToken,
      });
    }

  }, [initialToken]);

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
      eyebrow="Email verification"
      title={
        <>
          Confirm your
          <br />
          <em className="text-[#B98626]">
            email.
          </em>
        </>
      }
      description="Email verification protects workspace access and keeps your organization record trustworthy."
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          <Link
            to="/login"
            className="font-bold text-[#B98626] hover:underline"
          >
            Continue to sign in
          </Link>
        </p>
      }
    >
      {verify.isSuccess ? (
        <div className="space-y-4">
          <AuthNotice tone="success">
            Your email has been verified.
            You can now sign in normally.
          </AuthNotice>

          <Link
            to="/login"
            className="
              flex h-12 items-center
              justify-center rounded-[9px]
              bg-[#D9A441]
              text-[13px] font-bold
              text-[#080D18]
            "
          >
            Continue to sign in
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
                "The verification link is invalid or expired.",
              )}
            </AuthNotice>
          )}

          {verify.isError && (
            <div className="space-y-2 rounded-[9px] border border-[#E1D5BC] bg-[#F8F3E9] p-3.5">
              {resend.isSuccess ? (
                <AuthNotice tone="success">
                  If that account exists and isn't verified yet, a new link has been sent.
                </AuthNotice>
              ) : (
                <>
                  <p className="text-[11.5px] text-[#6B6152]">
                    Link expired? Request a new one.
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
                      {resend.isPending ? "Sending…" : "Resend"}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          <label className="block">
            <span className="mb-2 block text-[12px] font-semibold text-[#332A21]">
              Verification token
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
            className="
              h-12 w-full rounded-[9px]
              bg-[#D9A441]
              text-[13px] font-bold
              text-[#080D18]
              disabled:opacity-50
            "
          >
            {verify.isPending
              ? "Verifying…"
              : "Verify email"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}