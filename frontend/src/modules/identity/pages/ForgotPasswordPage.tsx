import {useState,
} from "react";
import {Link,
} from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { useForgotPassword } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";
import { useTranslation } from "react-i18next";

export function ForgotPasswordPage() {
  const forgot =
    useForgotPassword();

  const [email, setEmail] =
    useState("");
  
  const { t } = useTranslation();

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
      eyebrow={t("auth.forgot.eyebrow")}
      title={
      <>
       {t("auth.forgot.titleLine1")}
       <br />
       <em className="text-[var(--color-trace-gold-dark)]">
         {t("auth.forgot.titleEm")}
       </em>
      </>
     }
      description={t("auth.forgot.description")}
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          {t("auth.forgot.remember")}{" "}
          <Link
            to="/login"
            className="font-bold text-[var(--color-trace-gold-dark)] hover:underline"
          >
           {t("auth.forgot.return")}
          </Link>
        </p>
      }
    >
      {forgot.isSuccess ? (
        <AuthNotice tone="success">
          {t("auth.forgot.success")}
        </AuthNotice>
      ) : (
        <form
          onSubmit={submit}
          className="space-y-5"
        >
          {forgot.isError && (
            <AuthNotice tone="error">
              {getApiErrorMessage(
                t("auth.register.error"),
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
            className="h-12 w-full rounded-[var(--radius-sm)] bg-[var(--color-trace-gold)] text-[14px] font-semibold text-[var(--color-trace-navy)] transition hover:bg-[var(--color-trace-gold-dark)] disabled:cursor-not-allowed disabled:opacity-50">
            {forgot.isPending
              ? "Sending…"
              : "Send reset link"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}