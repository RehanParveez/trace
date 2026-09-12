import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { PasswordStrength, isPasswordStrong } from "../components/PasswordStrength";
import { useRegister } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";
import { useTranslation } from "react-i18next";

export function RegisterPage() {
  const navigate = useNavigate();
  const register = useRegister();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const passwordsMatch = password === confirmation;
  const { t } = useTranslation();

  async function submit(event: React.FormEvent) {
    event.preventDefault();

    if (!isPasswordStrong(password)) {
      return;
    }
    if (!passwordsMatch) {
      return;
    }

    try {
      await register.mutateAsync({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        organization_name: organizationName.trim(),
        password,
        password_confirmation: confirmation,
      });

      navigate("/login", {
        replace: true,
        state: {
          registrationSuccess: true,
        },
      });
    } catch {
    }
  }

  return (
    <AuthShell
      eyebrow={t("auth.register.eyebrow")}
      title={
       <>
        {t("auth.register.titleLine1")}
        <br />
        {t("auth.register.titleLine2")}
        <em className="text-[var(--color-trace-gold-dark)]">
          {t("auth.register.titleEm")}
        </em>
       </>
      }
      description={t("auth.register.description")}
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          {t("auth.register.hasAccount")}{" "}
          <Link
            to="/login"
            className="font-bold text-[var(--color-trace-gold-dark)] hover:underline"
          >
          {t("auth.register.signIn")}
          </Link>
        </p>
      }
    >
      <form
        onSubmit={submit}
        className="space-y-3"
      >
        {register.isError && (
          <AuthNotice tone="error">
            {getApiErrorMessage(
              register.error,
              "We could not create the workspace.",
            )}
          </AuthNotice>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <AuthField
            id="first_name"
            label={t("auth.register.firstName")}
            placeholder="First name"
            autoComplete="given-name"
            value={firstName}
            onChange={(event) =>
              setFirstName(event.target.value)
            }
            required
          />

          <AuthField
            id="last_name"
            label={t("auth.register.lastName")}
            placeholder="Last name"
            autoComplete="family-name"
            value={lastName}
            onChange={(event) =>
              setLastName(event.target.value)
            }
            required
          />
        </div>

        <AuthField
          id="email"
          type="email"
          label={t("auth.register.email")}
          placeholder="you@company.com"
          autoComplete="email"
          value={email}
          onChange={(event) =>
            setEmail(event.target.value)
          }
          required
        />

        <AuthField
          id="organization_name"
          label={t("auth.register.organization")}
          placeholder="Your construction company"
          value={organizationName}
          onChange={(event) =>
            setOrganizationName(event.target.value)
          }
          required
        />

        <AuthField
          id="password"
          type="password"
          label={t("auth.register.password")}
          placeholder="Create a strong password"
          autoComplete="new-password"
          value={password}
          onChange={(event) =>
            setPassword(event.target.value)
          }
          required
        />

        {password && (
          <div className="-mt-1">
            <PasswordStrength password={password} />
          </div>
        )}

        <AuthField
          id="password_confirmation"
          type="password"
          label={t("auth.register.confirm")}
          placeholder="Repeat your password"
          autoComplete="new-password"
          value={confirmation}
          onChange={(event) =>
            setConfirmation(event.target.value)
          }
          error={
           confirmation && !passwordsMatch
            ? t("auth.password.mismatch")
            : undefined
          }
          required
        />

        <button
          type="submit"
          disabled={
            register.isPending ||
            !firstName.trim() ||
            !lastName.trim() ||
            !email.trim() ||
            !organizationName.trim() ||
            !isPasswordStrong(password) ||
            !passwordsMatch
          }
          className="h-12 w-full rounded-[var(--radius-sm)] bg-[var(--color-trace-gold)] text-[14px] font-semibold text-[var(--color-trace-navy)] transition hover:bg-[var(--color-trace-gold-dark)] disabled:cursor-not-allowed disabled:opacity-50">
          {register.isPending
           ? t("auth.register.submitting")
           : t("auth.register.submit")}
        </button>
      </form>
    </AuthShell>
  );
}