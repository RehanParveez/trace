import {useState,
} from "react";
import {Link,
} from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { useForgotPassword } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";

export function ForgotPasswordPage() {
  const forgot =
    useForgotPassword();

  const [email, setEmail] =
    useState("");

  function submit(
    event: React.FormEvent,
  ) {
    event.preventDefault();

    forgot.mutate({
      email: email.trim().toLowerCase(),
    });
  }

  return (
    <AuthShell
      eyebrow="Account recovery"
      title={
        <>
          Find your way
          <br />
          <em className="text-[#B98626]">
            back.
          </em>
        </>
      }
      description="Enter your work email and Trace will send a secure password-reset link if the account is eligible."
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          Remember your password?{" "}
          <Link
            to="/login"
            className="font-bold text-[#B98626] hover:underline"
          >
            Return to sign in
          </Link>
        </p>
      }
    >
      {forgot.isSuccess ? (
        <AuthNotice tone="success">
          If an account exists for that email,
          a password-reset message has been
          sent.
        </AuthNotice>
      ) : (
        <form
          onSubmit={submit}
          className="space-y-5"
        >
          {forgot.isError && (
            <AuthNotice tone="error">
              {getApiErrorMessage(
                forgot.error,
              )}
            </AuthNotice>
          )}

          <AuthField
            id="email"
            type="email"
            label="Work email"
            placeholder="you@company.com"
            autoComplete="email"
            value={email}
            onChange={(event) =>
              setEmail(
                event.target.value,
              )
            }
            required
          />

          <button
            type="submit"
            disabled={
              forgot.isPending ||
              !email
            }
            className="
              h-12 w-full rounded-[9px]
              bg-[#D9A441]
              text-[13px] font-bold
              text-[#080D18]
              disabled:opacity-50
            "
          >
            {forgot.isPending
              ? "Sending…"
              : "Send reset link"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}