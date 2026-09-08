import {useEffect, useState,
} from "react";
import {Link, useLocation, useNavigate,
} from "react-router-dom";
import { AuthField } from "../components/AuthField";
import { AuthNotice } from "../components/AuthNotice";
import { AuthShell } from "../components/AuthShell";
import { useLogin } from "../hooks/useIdentity";
import { getApiErrorMessage } from "../utils/api-error";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const login = useLogin();

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const locationState = location.state as {
    from?: { pathname?: string; search?: string };
    registrationSuccess?: boolean;
    passwordReset?: boolean;
  } | null;

  const from =
    (locationState?.from?.pathname ?? "/app/profile") +
    (locationState?.from?.search ?? "");
  useEffect(() => {
    if (login.isSuccess) {
      navigate(from, {
        replace: true,
      });
    }
  }, [
    login.isSuccess,
    navigate,
    from,
  ]);

  function submit(event: React.FormEvent) {
  event.preventDefault();

  login.mutate({
    email: email.trim().toLowerCase(),
    password,
  });
}

  return (
    <AuthShell
      eyebrow="Workspace access"
      title={
        <>
          Welcome
          <br />
          <em className="text-[var(--color-trace-gold-dark)]">
            back.
          </em>
        </>
      }
      description="Sign in to your Trace workspace to see projects, drawings, quantities, site progress and the operational record behind the work."
      footer={
        <div className="flex flex-col gap-3 text-center text-[12px] text-[#6B6152]">
          <p>
            Don't have a workspace yet?{" "}
            <Link
              to="/register"
              className="text-[var(--color-trace-gold-dark)] hover:underline"
            >
              Create one
            </Link>
          </p>

          <Link
            to="/"
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            ← Back to Trace
          </Link>
        </div>
        }
      >
        
      <form
        onSubmit={submit}
        className="space-y-4"
      >
        {locationState?.registrationSuccess && !login.isError && (
          <AuthNotice tone="success">
            Workspace created. Check your email for a verification link, then sign in.
          </AuthNotice>
        )}

        {locationState?.passwordReset && !login.isError && (
          <AuthNotice tone="success">
            Your password has been reset. Sign in with your new password.
          </AuthNotice>
        )}

        {login.isError && (
          <AuthNotice tone="error">
            {getApiErrorMessage(
              login.error,
              "Unable to sign in. Check your credentials and try again.",
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
            setEmail(event.target.value)
          }
          required
        />

        <AuthField
          id="password"
          type="password"
          label="Password"
          placeholder="Enter your password"
          autoComplete="current-password"
          value={password}
          onChange={(event) =>
            setPassword(event.target.value)
          }
          required
          hint={
            <Link
              to="/forgot-password"
              className="text-[#B98626] hover:underline"
            >
              Forgot password?
            </Link>
          }
        />

        <button
          type="submit"
          disabled={
            login.isPending ||
            !email ||
            !password
          }
          className="h-12 w-full rounded-[var(--radius-sm)] bg-[var(--color-trace-gold)] text-[14px] font-semibold text-[var(--color-trace-navy)] transition hover:bg-[var(--color-trace-gold-dark)] disabled:cursor-not-allowed disabled:opacity-50">
          {login.isPending
            ? "Signing in…"
            : "Sign in to Trace"}
        </button>
      </form>
    </AuthShell>
  );
}