import type {ReactNode,
} from "react";

type AuthNoticeProps = {
  tone?: "error" | "success" | "info";
  children: ReactNode;
};

const styles = {
  error:
    "border-[var(--color-danger)]/25 bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  success:
    "border-[var(--color-success)]/25 bg-[var(--color-success-bg)] text-[var(--color-success)]",
  info:
    "border-[var(--color-info)]/25 bg-[var(--color-info-bg)] text-[var(--color-info)]",
};

export function AuthNotice({
  tone = "info",
  children,
}: AuthNoticeProps) {
  return (
    <div
      className={[
        "rounded-[var(--radius-sm)] border",
        "px-4 py-3.5",
        "text-[14px] leading-5",
        styles[tone],
      ].join(" ")}
    >
      {children}
    </div>
  );
}