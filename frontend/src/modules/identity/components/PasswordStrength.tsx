import { getPasswordChecks } from "../utils/identity.password";
import { useTranslation } from "react-i18next";

type PasswordStrengthProps = {
  password: string;
};

const checks = [
  ["length", "auth.password.length"],
  ["uppercase", "auth.password.uppercase"],
  ["lowercase", "auth.password.lowercase"],
  ["number", "auth.password.number"],
  ["special", "auth.password.special"],
  ["notCommon", "auth.password.notCommon"],
] as const;

export function PasswordStrength({
  password,
}: PasswordStrengthProps) {
  const { t } = useTranslation();

  const result = getPasswordChecks(password);

  const passed = Object.values(result).filter(Boolean).length;

  const percentage =
    password.length === 0
      ? 0
      : Math.round((passed / checks.length) * 100);

  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
          {t("auth.passwordStrength")}
        </span>

        <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
          {passed}/{checks.length}
        </span>
      </div>

      <div className="mb-3.5 h-1.5 overflow-hidden rounded-full bg-[var(--color-border)]">
        <div
          className="h-full rounded-full bg-[var(--color-trace-gold)] transition-all"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
        {checks.map(([key, labelKey]) => {
          const valid = result[key];

          return (
            <div key={key} className="flex items-center gap-2 text-[13px]">
              <span
                className={[
                  "grid h-4 w-4 place-items-center rounded-full text-[9px] font-bold",
                  valid
                   ? "bg-[var(--color-trace-gold)] text-[var(--color-trace-navy)]"
                   : "border border-[var(--color-border-strong)] text-transparent",
                ].join(" ")}
              >
                ✓
              </span>

              <span
                className={
                 valid
                 ? "text-[var(--color-text-primary)]"
                 : "text-[var(--color-text-muted)]"
                }
              >
                {t(labelKey)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function isPasswordStrong(password: string): boolean {
  return Object.values(getPasswordChecks(password)).every(Boolean);
}
