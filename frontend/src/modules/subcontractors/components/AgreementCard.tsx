import { Badge, Icon } from "../../organizations/components/OrganizationUi";
import type { SubcontractAgreementDetail } from "../types/subcontractor.types";
import { formatMoney, getAgreementStatusTone } from "../utils/subcontractor.utils";

export function AgreementCard({ agreement, subcontractorName, onOpen }: { agreement: SubcontractAgreementDetail; subcontractorName: string; onOpen: () => void }) {
  return (
    <button type="button" onClick={onOpen} className="w-full rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 text-left transition hover:border-[var(--color-border-strong)] hover:shadow-[0_8px_22px_rgba(90,70,40,0.06)]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-[Archivo] text-[15px] font-bold text-[var(--color-text-primary)]">{subcontractorName}</span>
        <Badge tone={getAgreementStatusTone(agreement.status)}>{agreement.status}</Badge>
      </div>
      <p className="mt-1 line-clamp-2 text-[12.5px] text-[var(--color-text-secondary)]">{agreement.scope_description}</p>
      <div className="mt-3 flex items-center justify-between border-t border-[var(--color-border)] pt-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[var(--color-text-muted)]">Contract value</span>
        <span className="font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatMoney(agreement.contract_value)}</span>
      </div>
      <div className="mt-1.5 flex items-center gap-1.5 text-[12px] font-semibold text-[var(--color-trace-gold-dark)]">
        View agreement <Icon name="arrow" size={11} />
      </div>
    </button>
  );
}