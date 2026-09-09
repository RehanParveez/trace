import { Badge, Button, EmptyState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import type { ProgressClaim } from "../types/verification.types";
import { formatClaimDate, formatClaimPercentage, formatClaimStatus, getClaimStatusTone } from "../utils/verification.utils";

interface ProgressClaimTableProps {
  claims: ProgressClaim[];
  canCreate: boolean;
  onCreate: () => void;
  onView: (claim: ProgressClaim) => void;
}

export function ProgressClaimTable({ claims, canCreate, onCreate, onView }: ProgressClaimTableProps) {
  return (
    <Panel>
      <PanelHeader
        eyebrow="PROGRESS VERIFICATION"
        title="Progress claims"
        description="Claims of physical progress against approved BOQ items, backed by photo evidence."
        action={canCreate ? <Button variant="primary" size="sm" onClick={onCreate}>New claim</Button> : null}
      />

      {claims.length === 0 ? (
        <EmptyState
          icon="check"
          title="No progress claims yet"
          description="Progress claims appear here once BOQ items are approved and site teams start reporting physical progress against them."
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[600px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Percentage</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                  <td className="px-4 py-3.5 text-[13px] text-[var(--color-text-primary)]">{formatClaimDate(claim.claim_date)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[12.5px] font-semibold text-[var(--color-text-primary)]">{formatClaimPercentage(claim.claimed_percentage)}</td>
                  <td className="px-4 py-3.5"><Badge tone={getClaimStatusTone(claim.status)}>{formatClaimStatus(claim.status)}</Badge></td>
                  <td className="px-4 py-3.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => onView(claim)}>View</Button>
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