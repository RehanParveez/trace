import {useMemo, useState,
} from "react";
import {Link, useNavigate, useSearchParams,
} from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { PasswordStrength } from "../components/PasswordStrength";
import { useResetPassword } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";

export function ResetPasswordPage() {
  const navigate = useNavigate();

  const [params] =
    useSearchParams();

  const reset =
    useResetPassword();

  const token = useMemo(
    () =>
      params.get("token") ??
      "",
    [params],
  );

  const [password, setPassword] =
    useState("");

  const [confirmation, setConfirmation] =
    useState("");

  const matches =
    password === confirmation;

  function isPasswordStrong(password: string): boolean {
  return (
    password.length >= 8 &&
    /[A-Z]/.test(password) &&
    /[a-z]/.test(password) &&
    /[0-9]/.test(password)
  );
}

  function submit(
    event: React.FormEvent,
  ) {
    event.preventDefault();

    if (
      !token ||
      !isPasswordStrong(password) ||
      !matches
    ) {
      return;
    }

    reset.mutate(
      {
        token,
        password,
        password_confirmation:
          confirmation,
      },
      {
        onSuccess: () => {
          navigate("/login", {
            replace: true,
            state: {
              passwordReset: true,
            },
          });
        },
      },
    );
  }

  if (!token) {
    return (
      <AuthShell
        eyebrow="Password recovery"
        title={
          <>
            Reset link
            <br />
            <em className="text-[#B98626]">
              unavailable.
            </em>
          </>
        }
        description="The password-reset link is missing or incomplete."
      >
        <AuthNotice tone="error">
          Request a new password-reset link
          and try again.
        </AuthNotice>

        <Link
          to="/forgot-password"
          className="mt-5 block text-center text-[12px] font-bold text-[#B98626]"
        >
          Request another link
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow="Password recovery"
      title={
        <>
          Create a new
          <br />
          <em className="text-[#B98626]">
            password.
          </em>
        </>
      }
      description="Choose a strong password that protects your Trace workspace."
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          <Link
            to="/login"
            className="font-bold text-[#B98626]"
          >
            Return to sign in
          </Link>
        </p>
      }
    >
      <form
        onSubmit={submit}
        className="space-y-4"
      >
        {reset.isError && (
          <AuthNotice tone="error">
            {getApiErrorMessage(
              reset.error,
              "The reset link is invalid or expired.",
            )}
          </AuthNotice>
        )}

        <AuthField
          id="password"
          type="password"
          label="New password"
          placeholder="Create a strong password"
          autoComplete="new-password"
          value={password}
          onChange={(event) =>
            setPassword(
              event.target.value,
            )
          }
          required
        />

        {password && (
          <PasswordStrength
            password={password}
          />
        )}

        <AuthField
          id="password_confirmation"
          type="password"
          label="Confirm password"
          placeholder="Repeat your password"
          autoComplete="new-password"
          value={confirmation}
          onChange={(event) =>
            setConfirmation(
              event.target.value,
            )
          }
          error={
            confirmation &&
            !matches
              ? "Passwords do not match."
              : undefined
          }
          required
        />

        <button
          type="submit"
          disabled={
            reset.isPending ||
            !isPasswordStrong(password) ||
            !matches
          }
          className="
            h-12 w-full rounded-[9px]
            bg-[#D9A441]
            text-[13px] font-bold
            text-[#080D18]
            disabled:opacity-50
          "
        >
          {reset.isPending
            ? "Updating password…"
            : "Set new password"}
        </button>
      </form>
    </AuthShell>
  );
}