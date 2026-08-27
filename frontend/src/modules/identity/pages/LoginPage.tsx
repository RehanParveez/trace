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

  const from =
    (
      location.state as {
        from?: {
          pathname?: string;
        };
      } | null
    )?.from?.pathname ??
    "/app/profile";

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

  function submit(
    event: React.FormEvent,
  ) {
    event.preventDefault();

    console.log('=== LOGIN SUBMIT DEBUG ===');
    console.log('Email:', email.trim().toLowerCase());
    console.log('Password:', password ? '***' : '(empty)');
    console.log('Payload being sent:', {
      email: email.trim().toLowerCase(),
      password,
    });

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
          <em className="text-[#B98626]">
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
              className="font-bold text-[#B98626] hover:underline"
            >
              Create one
            </Link>
          </p>

          <Link
            to="/"
            className="text-[#8B806F] hover:text-[#332A21]"
          >
            ← Back to Trace
          </Link>
        </div>
      }
    >
      <form
        onSubmit={submit}
        className="space-y-5"
      >
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
          className="
            h-12 w-full rounded-[9px]
            bg-[#D9A441]
            px-5
            text-[13px] font-bold
            text-[#080D18]
            shadow-[0_5px_16px_rgba(217,164,65,.18)]
            transition
            hover:bg-[#C99532]
            disabled:cursor-not-allowed
            disabled:opacity-50
          "
        >
          {login.isPending
            ? "Signing in…"
            : "Sign in to Trace"}
        </button>
      </form>
    </AuthShell>
  );
}