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
        <EmptyState icon="check" title="No progress claims yet" description="Create a claim once BOQ items are approved and work is underway." />
      ) : (
        <TableShell>
          <table className="w-full min-w-[600px] text-left">
            <thead className="bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Percentage</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id} className="border-t border-[#e1d5bc] transition hover:bg-[#f5efe3]">
                  <td className="px-4 py-3.5 text-[11.5px] text-[#191410]">{formatClaimDate(claim.claim_date)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-[11px] font-semibold text-[#191410]">{formatClaimPercentage(claim.claimed_percentage)}</td>
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