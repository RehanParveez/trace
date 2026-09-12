import { Link } from "react-router-dom";
import { Icon } from "../../organizations/components/OrganizationUi";

interface QuotaLimitNoticeProps {
  message: string;
}

export function QuotaLimitNotice({ message }: QuotaLimitNoticeProps) {
  return (
    <div className="flex items-start gap-3 rounded-[var(--radius-md)] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-[var(--color-surface)] text-[var(--color-warning)]">
        <Icon name="alert" size={15} />
      </div>

      <div className="min-w-0">
        <p className="text-[13px] leading-5 text-[var(--color-text-primary)]">{message}</p>
        <Link
          to="/app/subscription"
          className="mt-1 inline-block text-[12.5px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline"
        >
          View plans and upgrade
        </Link>
      </div>
    </div>
  );
}