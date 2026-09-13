import { Badge, Button, EmptyState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { ProgressClaim } from "../types/verification.types";
import { formatClaimDate, formatClaimPercentage, formatClaimStatus, getClaimStatusTone } from "../utils/verification.utils";
import { useTranslation } from "react-i18next";

interface ProgressClaimTableProps {
  claims: ProgressClaim[];
  canCreate: boolean;
  onCreate: () => void;
  onView: (claim: ProgressClaim) => void;
}

export function ProgressClaimTable({ claims, canCreate, onCreate, onView }: ProgressClaimTableProps) {
  const { t } = useTranslation();
  return (
    <Panel>
      <PanelHeader
        eyebrow={t("verification.table.eyebrow")}
        title={t("verification.table.title")}
        description={t("verification.table.description")}
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>New claim</Button> : null}
      />

      {claims.length === 0 ? (
        <EmptyState
          icon="check"
          title={t("verification.table.emptyTitle")}
          description={t("verification.table.emptyDesc")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[600px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("verification.table.colDate")}</th>
                <th className="px-4 py-3 text-right">{t("verification.table.colPercentage")}</th>
                <th className="px-4 py-3">{t("verification.table.colStatus")}</th>
                <th className="px-4 py-3 text-right">{t("verification.table.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5 text-[13px] text-[var(--color-text-primary)]">{formatClaimDate(claim.claim_date)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">{formatClaimPercentage(claim.claimed_percentage)}</td>
                  <td className="px-4 py-3.5"><Badge tone={getClaimStatusTone(claim.status)}>{formatClaimStatus(claim.status)}</Badge></td>
                  <td className="px-4 py-3.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => onView(claim)}>{t("verification.table.view")}</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}