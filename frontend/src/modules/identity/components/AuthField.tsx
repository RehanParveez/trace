import type {InputHTMLAttributes, ReactNode
} from "react";

type AuthFieldProps =
  InputHTMLAttributes<HTMLInputElement> & {
    label: string;
    error?: string;
    hint?:  ReactNode;
  };

export function AuthField({
  label,
  error,
  hint,
  id,
  ...props
}: AuthFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center justify-between text-[13px] font-semibold text-[var(--color-text-primary)]">
        <span>{label}</span>

        {hint && (
          <span className="font-normal text-[var(--color-text-muted)]">
            {hint}
          </span>
        )}
      </span>

      <input
        id={id}
        {...props}
        className={[
          "h-12 w-full rounded-[var(--radius-sm)]",
          "border bg-[var(--color-surface)]",
          "px-3.5 text-[14px]",
          "text-[var(--color-text-primary)]",
          "outline-none transition",
          "placeholder:text-[var(--color-text-muted)]",
          "focus:border-[var(--color-trace-gold-dark)]",
          "focus:ring-2 focus:ring-[var(--color-trace-gold)]/20",
          error
            ? "border-[var(--color-danger)]"
            : "border-[var(--color-border)]",
        ].join(" ")}
      />

      {error && (
        <span className="mt-1.5 block text-[13px] text-[var(--color-danger)]">
          {error}
        </span>
      )}
    </label>
  );
}