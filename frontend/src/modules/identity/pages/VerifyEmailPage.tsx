import {useEffect, useState,
} from "react";
import {Link, useSearchParams,
} from "react-router-dom";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { useVerifyEmail } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";

export function VerifyEmailPage() {
  const [params] =
    useSearchParams();

  const verify =
    useVerifyEmail();

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