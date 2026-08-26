import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { PasswordStrength } from "../components/PasswordStrength";
import { useRegister } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";

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

  function isPasswordStrong(password: string): boolean {
    return (
      password.length >= 12 &&
      /[A-Z]/.test(password) &&
      /[a-z]/.test(password) &&
      /[0-9]/.test(password)
    );
  }

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
      eyebrow="Create workspace"
      title={
        <>
          Start with a
          <br />
          clear
          <em className="text-[#B98626]">
            record.
          </em>
        </>
      }
      description="Create your Trace workspace and bring your project information into one operational system."
      footer={
        <p className="text-center text-[12px] text-[#6B6152]">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-bold text-[#B98626] hover:underline"
          >
            Sign in
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
            label="First name"
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
            label="Last name"
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
          label="Work email"
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
          label="Organization"
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
          label="Password"
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
          label="Confirm password"
          placeholder="Repeat your password"
          autoComplete="new-password"
          value={confirmation}
          onChange={(event) =>
            setConfirmation(event.target.value)
          }
          error={
            confirmation && !passwordsMatch
              ? "Passwords do not match."
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
          className="
            mt-1
            h-12
            w-full
            rounded-[9px]
            bg-[#D9A441]
            text-[13px]
            font-bold
            text-[#080D18]
            transition
            hover:bg-[#C99532]
            disabled:cursor-not-allowed
            disabled:opacity-50
          "
        >
          {register.isPending
            ? "Creating workspace…"
            : "Create Trace workspace"}
        </button>
      </form>
    </AuthShell>
  );
}