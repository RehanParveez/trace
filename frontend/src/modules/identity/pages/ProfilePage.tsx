import {useState,
} from "react";
import {Link,
} from "react-router-dom";
import { AuthNotice } from "../components/AuthNotice";
import { AuthField } from "../components/AuthField";
import {useChangePassword, useLogout, useLogoutAll,
} from "../hooks/useIdentity";
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

  function isPasswordStrong(password: string): boolean {
  return (
    password.length >= 8 &&
    /[A-Z]/.test(password) &&
    /[a-z]/.test(password) &&
    /[0-9]/.test(password)
  );
}

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
    <div className="min-h-screen bg-[#F5EFE3]">
      <div className="mx-auto max-w-[1200px] px-6 py-8 lg:px-10">

        <div className="mb-8">
          <p className="font-mono text-[10px] uppercase tracking-[.14em] text-[#B98626]">
            Identity
          </p>

          <div className="mt-2 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <h1 className="font-['Fraunces'] text-4xl text-[#191410]">
                My profile
              </h1>

              <p className="mt-2 text-[13px] text-[#776D5E]">
                Manage your identity,
                organization access and
                security.
              </p>
            </div>

            <Link
              to="/app/profile"
              className="text-[12px] font-bold text-[#B98626]"
            >
              ← Back to workspace
            </Link>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">

          <section className="rounded-[12px] border border-[#E1D5BC] bg-[#FBF8F2] p-6 shadow-[0_2px_10px_rgba(50,42,33,.035)]">
            <div className="mb-6 flex items-center gap-4">
              <div className="grid h-14 w-14 place-items-center rounded-[12px] bg-[#0D1424] font-['Fraunces'] text-xl text-[#D9A441]">
                {user.first_name[0]}
                {user.last_name[0]}
              </div>

              <div>
                <h2 className="font-['Fraunces'] text-xl text-[#191410]">
                  {user.first_name}{" "}
                  {user.last_name}
                </h2>

                <p className="mt-1 font-mono text-[9px] uppercase tracking-[.1em] text-[#8B806F]">
                  {user.role.name}
                </p>
              </div>
            </div>

            <div className="space-y-1">
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

          <section className="rounded-[12px] border border-[#E1D5BC] bg-[#FBF8F2] p-6 shadow-[0_2px_10px_rgba(50,42,33,.035)]">
            <div className="mb-6">
              <p className="font-mono text-[9px] uppercase tracking-[.12em] text-[#B98626]">
                Security
              </p>

              <h2 className="mt-1 font-['Fraunces'] text-xl">
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

        <section className="mt-5 rounded-[12px] border border-[#E1D5BC] bg-[#FBF8F2] p-6">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[.12em] text-[#B98626]">
                Sessions
              </p>

              <h2 className="mt-1 font-['Fraunces'] text-xl">
                Secure your workspace
              </h2>

              <p className="mt-2 max-w-xl text-[12px] leading-5 text-[#776D5E]">
                Sign out from every active
                refresh-token session associated
                with this account.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={() =>
                  logout.mutate()
                }
                disabled={logout.isPending}
                className="h-10 rounded-[8px] border border-[#D8CDB9] px-4 text-[11px] font-bold text-[#332A21]"
              >
                {logout.isPending
                  ? "Signing out…"
                  : "Sign out"}
              </button>

              <button
                onClick={() =>
                  logoutAll.mutate()
                }
                disabled={logoutAll.isPending}
                className="h-10 rounded-[8px] bg-[#C24A3A] px-4 text-[11px] font-bold text-white"
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
    <div className="flex items-center justify-between border-b border-[#E8DFCF] py-3 last:border-b-0">
      <span className="font-mono text-[9px] uppercase tracking-[.08em] text-[#8B806F]">
        {label}
      </span>

      <span
        className={[
          "max-w-[60%] truncate text-right text-[12px] font-semibold",
          positive
            ? "text-[#176F49]"
            : "text-[#332A21]",
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}