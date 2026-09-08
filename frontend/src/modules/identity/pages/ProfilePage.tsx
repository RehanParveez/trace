import {useState,
} from "react";
import {Link,
} from "react-router-dom";
import { AuthNotice } from "../components/AuthNotice";
import { AuthField } from "../components/AuthField";
import {useChangePassword, useLogout, useLogoutAll,
} from "../hooks/useIdentity";
import { PasswordStrength, isPasswordStrong } from "../components/PasswordStrength";
import { useAuthStore } from "../store/auth.store";
import { getApiErrorMessage } from "../utils/api-error";

export function ProfilePage() {
  const user = useAuthStore(
    (state) => state.user,
  );

  const changePassword =
    useChangePassword();

  const logout =
    useLogout();

  const logoutAll =
    useLogoutAll();

  const [currentPassword, setCurrentPassword] =
    useState("");

  const [newPassword, setNewPassword] =
    useState("");

  const [confirmation, setConfirmation] =
    useState("");

  if (!user) {
    return null;
  }

  const passwordsMatch =
    newPassword === confirmation;

  function submitPassword(
    event: React.FormEvent,
  ) {
    event.preventDefault();

    if (
      !currentPassword ||
      !isPasswordStrong(newPassword) ||
      !passwordsMatch
    ) {
      return;
    }

    changePassword.mutate({
      current_password:
        currentPassword,

      new_password:
        newPassword,

      new_password_confirmation:
        confirmation,
    });
  }

  return (
    <div className="min-h-screen bg-[var(--color-workspace)]">
      <div className="mx-auto max-w-[1200px] px-6 py-10 lg:px-10">

        <div className="mb-9">
         <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-trace-gold-dark)]">
          Identity
        </p>

        <div className="mt-2.5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
         <div>
          <h1 className="font-['Fraunces'] text-[36px] font-semibold text-[var(--color-text-primary)]">
            My profile
          </h1>
          <p className="mt-2 text-[15px] text-[var(--color-text-secondary)]">
           Manage your identity, organization access and security.
          </p>
          </div>

          <Link
            to="/app/organization"
            className="text-[13px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline"
          >
          ← Back to workspace
        </Link>
       </div>
    </div>

        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">

          <section className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm">
            <div className="mb-6 flex items-center gap-4">
              <div className="grid h-14 w-14 place-items-center rounded-[12px] bg-[var(--color-trace-navy)] font-['Fraunces'] text-xl text-[var(--color-trace-gold)]">
                {user.first_name[0]}
                {user.last_name[0]}
              </div>

              <div>
                <h2 className="font-['Fraunces'] text-[22px] text-[var(--color-text-primary)]">
                 {user.first_name} {user.last_name}
                </h2>

                <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
                 {user.role.name}
                </p>
              </div>
            </div>

            <div className="space-y-0">
              <ProfileRow
                label="Email"
                value={user.email}
              />

              <ProfileRow
                label="Organization"
                value={
                  user.organization.name
                }
              />

              <ProfileRow
                label="Workspace"
                value={
                  user.organization.slug
                }
              />

              <ProfileRow
                label="Role"
                value={user.role.name}
              />

              <ProfileRow
                label="Email status"
                value={
                  user.is_verified
                    ? "Verified"
                    : "Unverified"
                }
                positive={
                  user.is_verified
                }
              />

              <ProfileRow
                label="Account status"
                value={
                  user.is_active
                    ? "Active"
                    : "Inactive"
                }
                positive={
                  user.is_active
                }
              />
            </div>
          </section>

          <section className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm">
            <div className="mb-6">
              <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-trace-gold-dark)]">
               Security
              </p>

              <h2 className="mt-1.5 font-['Fraunces'] text-[22px]">
               Change password
              </h2>
            </div>

            {changePassword.isSuccess && (
              <div className="mb-4">
                <AuthNotice tone="success">
                  Your password has been
                  updated.
                </AuthNotice>
              </div>
            )}

            {changePassword.isError && (
              <div className="mb-4">
                <AuthNotice tone="error">
                  {getApiErrorMessage(
                    changePassword.error,
                  )}
                </AuthNotice>
              </div>
            )}

            <form
              onSubmit={submitPassword}
              className="space-y-4"
            >
              <AuthField
                label="Current password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) =>
                  setCurrentPassword(
                    event.target.value,
                  )
                }
                required
              />

              <AuthField
                label="New password"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) =>
                  setNewPassword(
                    event.target.value,
                  )
                }
                required
              />

              {newPassword ? (
                <PasswordStrength password={newPassword} />
              ) : null}

              <AuthField
                label="Confirm new password"
                type="password"
                autoComplete="new-password"
                value={confirmation}
                onChange={(event) =>
                  setConfirmation(
                    event.target.value,
                  )
                }
                error={
                  confirmation &&
                  !passwordsMatch
                    ? "Passwords do not match."
                    : undefined
                }
                required
              />

              <button
                type="submit"
                disabled={
                  changePassword.isPending ||
                  !currentPassword ||
                  !isPasswordStrong(
                  newPassword,
                  ) ||
                  !passwordsMatch
                }
                className="
                 h-11 w-full rounded-[8px]
                 bg-[#0D1424]
                 text-[12px] font-bold
                text-[#FBF8F2]
                disabled:opacity-40
               "
              >
             {changePassword.isPending
              ? "Updating…"
              : "Update password"}
             </button>
            </form>
          </section>
        </div>

        <section className="mt-6 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div>
              <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-trace-gold-dark)]">
                Sessions
              </p>

              <h2 className="mt-1.5 font-['Fraunces'] text-[22px]">
                Secure your workspace
              </h2>

              <p className="mt-2 max-w-xl text-[14px] leading-6 text-[var(--color-text-secondary)]">
                Sign out from every active refresh-token session associated with this account.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => logout.mutate()}
                disabled={logout.isPending}
                className="h-10 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 text-[13px] font-semibold text-[var(--color-text-primary)]"
              >
              {logout.isPending
                ? "Signing out…"
                : "Sign out"}
              </button>

              <button
                onClick={() => logoutAll.mutate()}
                disabled={logout.isPending || logoutAll.isPending}
                className="h-10 rounded-[var(--radius-sm)] bg-[var(--color-danger)] px-4 text-[13px] font-semibold text-white"
              >
              {logoutAll.isPending
                ? "Revoking…"
                : "Revoke all sessions"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function ProfileRow({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--color-border)] py-3.5 last:border-b-0">
      <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
        {label}
      </span>

      <span
        className={[
          "max-w-[60%] truncate text-right text-[14px] font-semibold",
          positive ? "text-[var(--color-success)]" : "text-[var(--color-text-primary)]",
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}