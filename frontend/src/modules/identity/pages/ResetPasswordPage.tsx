import {useMemo, useState,
} from "react";
import {Link, useNavigate, useSearchParams,
} from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { PasswordStrength, isPasswordStrong } from "../components/PasswordStrength";
import { useResetPassword } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";
import { useTranslation } from "react-i18next";

export function ResetPasswordPage() {
  const navigate = useNavigate();

  const [params] =
    useSearchParams();

  const { t } = useTranslation();

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
        eyebrow={t("auth.reset.eyebrow")}
        title={
         <>
         {t("auth.reset.titleLine1")}
         <br />
         <em className="text-[var(--color-trace-gold-dark)]">
          {t("auth.reset.titleEm")}
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
          className="mt-5 block text-center text-[12px] font-bold text-[var(--color-trace-gold-dark)]"
        >
          {t("auth.reset.requestAnother")}
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow={t("auth.reset.eyebrow")}
      title={
       <>
        {t("auth.reset.titleLine1")}
        <br />
        <em className="text-[var(--color-trace-gold-dark)]">
         {t("auth.reset.titleEm")}
        </em>
      </>
    }
      description={t("auth.reset.description")}
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          <Link
            to="/login"
            className="font-bold text-[var(--color-trace-gold-dark)]"
          >
            {t("auth.reset.return")}
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
              t("auth.reset.error"),
            )}
          </AuthNotice>
        )}

        <AuthField
          id="password"
          type="password"
          label={t("auth.reset.newPassword")}
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
          label={t("auth.reset.confirm")}
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
              ? t("auth.password.mismatch")
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
          className="h-12 w-full rounded-[var(--radius-sm)] bg-[var(--color-trace-gold)] text-[14px] font-semibold text-[var(--color-trace-navy)] transition hover:bg-[var(--color-trace-gold-dark)] disabled:cursor-not-allowed disabled:opacity-50">
          {reset.isPending
            ? t("auth.reset.submitting")
            : t("auth.reset.submit")}
        </button>
      </form>
    </AuthShell>
  );
}