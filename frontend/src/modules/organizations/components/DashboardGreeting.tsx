import { LivePip } from "./OrganizationUi";
import { useTranslation } from "react-i18next";

function getGreeting(date: Date, t: (key: string) => string): string {
  const hour = date.getHours();
  if (hour < 12) return t("dashboard.greeting.morning");
  if (hour < 18) return t("dashboard.greeting.afternoon");
  return t("dashboard.greeting.evening");
}

interface DashboardGreetingProps {
  organizationName: string;
}

export function DashboardGreeting({ organizationName }: DashboardGreetingProps) {
  const { t } = useTranslation();
  const now = new Date();
  const greeting = getGreeting(now, t);

  const dateLabel = new Intl.DateTimeFormat("en-PK", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(now);

  return (
    <section className="overflow-hidden rounded-[var(--radius-lg)] border border-[#263356] bg-[linear-gradient(120deg,var(--color-trace-navy)_0%,var(--color-trace-navy-soft)_60%,var(--color-trace-navy-mid)_100%)] text-white shadow-[0_12px_32px_rgba(8,13,24,0.14)]">
      <div className="relative p-6 sm:p-7">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.028)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.028)_1px,transparent_1px)] bg-[length:28px_28px]" />

        <div className="pointer-events-none absolute -right-20 -top-24 h-56 w-56 rounded-full bg-[var(--color-trace-gold)]/[0.07] blur-3xl" />

        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2.5 text-[10px] font-bold uppercase tracking-[0.16em] text-[#8f9bb0]">
              <span className="h-px w-7 bg-[var(--color-trace-gold)]" />
              {dateLabel}
            </div>

            <h1 className="font-[Archivo] text-[28px] font-bold tracking-[-0.03em] text-white sm:text-[32px]">
              {greeting}, {organizationName}
            </h1>

            <p className="mt-2 max-w-xl text-[13px] leading-5 text-[#c7ced7]">
              {t("dashboard.greeting.subtitle")}
            </p>
          </div>

          <LivePip label={t("shell.workspaceOperational")} />
        </div>
      </div>
    </section>
  );
}