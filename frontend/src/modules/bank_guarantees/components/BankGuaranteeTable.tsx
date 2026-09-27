import { useState } from "react";
import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, StatCard, TableShell, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useMarkGuaranteeCalled, useReleaseBankGuarantee } from "../hooks/index.ts";
import { BankGuaranteeRenewDialog } from "./BankGuaranteeRenewDialog";
import type { BankGuarantee, ProjectBankGuaranteeSummary } from "../types/bank-guarantee.types";
import { formatGuaranteeDate, formatGuaranteeMoney, formatGuaranteeStatus, getGuaranteeStatusTone } from "../utils/bank-guarantee.utils";
import { useTranslation } from "react-i18next";

export function BankGuaranteeTable({ projectId, guarantees, summary, canManage, canRelease, onCreate }: {
  projectId: string; guarantees: BankGuarantee[]; summary?: ProjectBankGuaranteeSummary;
  canManage: boolean; canRelease: boolean; onCreate: () => void;
}) {
  const { t } = useTranslation();
  const releaseGuarantee = useReleaseBankGuarantee(projectId);
  const markCalled = useMarkGuaranteeCalled(projectId);
  const { showToast } = useToast();
  const [renewing, setRenewing] = useState<BankGuarantee | null>(null);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label={t("bankGuarantees.stat.active")} value={summary?.active_count ?? "…"} note={t("bankGuarantees.stat.activeNote")} icon="check" tone="blue" />
        <StatCard label={t("bankGuarantees.stat.expiringSoon")} value={summary?.expiring_soon_count ?? "…"} note={t("bankGuarantees.stat.expiringSoonNote")} icon="alert" tone={summary && summary.expiring_soon_count > 0 ? "gold" : "green"} />
        <StatCard label={t("bankGuarantees.stat.expired")} value={summary?.expired_count ?? "…"} note={t("bankGuarantees.stat.expiredNote")} icon="alert" tone={summary && summary.expired_count > 0 ? "red" : "green"} />
      </div>

      <Panel>
        <PanelHeader eyebrow={t("bankGuarantees.table.eyebrow")} title={t("bankGuarantees.table.title")} description={t("bankGuarantees.table.description")} action={canManage ? <Button variant="primary" size="sm" onClick={onCreate}><Icon name="plus" size={13} />{t("bankGuarantees.table.record")}</Button> : null} />

        {guarantees.length === 0 ? (
          <EmptyState icon="budget" title={t("bankGuarantees.table.emptyTitle")} description={t("bankGuarantees.table.emptyDesc")} action={canManage ? <Button variant="primary" size="sm" onClick={onCreate}>{t("bankGuarantees.table.record")}</Button> : undefined} />
        ) : (
          <TableShell>
            <table className="w-full min-w-[720px] text-left">
              <thead className="bg-[var(--color-surface-muted)]"><tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"><th className="px-4 py-3">{t("bankGuarantees.table.colGuarantee")}</th><th className="px-4 py-3">{t("bankGuarantees.table.colBank")}</th><th className="px-4 py-3 text-right">{t("bankGuarantees.table.colAmount")}</th><th className="px-4 py-3">{t("bankGuarantees.table.colExpiry")}</th><th className="px-4 py-3">{t("bankGuarantees.table.colStatus")}</th><th className="px-4 py-3 text-right">{t("bankGuarantees.table.colActions")}</th></tr></thead>
              <tbody>
                {guarantees.map((g) => (
                  <tr key={g.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3.5 text-[13.5px] font-semibold text-[var(--color-text-primary)]">{g.guarantee_number}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{g.issuing_bank}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">{formatGuaranteeMoney(g.amount, g.currency)}</td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatGuaranteeDate(g.expiry_date)}</td>
                    <td className="px-4 py-3.5"><Badge tone={getGuaranteeStatusTone(g.status, g.is_expired, g.is_expiring_soon)}>{g.is_expired ? t("bankGuarantees.table.expired") : g.is_expiring_soon ? t("bankGuarantees.table.expiringSoon") : formatGuaranteeStatus(g.status)}</Badge></td>
                    <td className="px-4 py-3.5 text-right">
                      {g.status === "ACTIVE" ? (
                        <div className="flex justify-end gap-2">
                          {canManage ? <Button variant="secondary" size="sm" onClick={() => setRenewing(g)}>{t("bankGuarantees.table.renew")}</Button> : null}
                          {canRelease ? (
                            <Button variant="ghost" size="sm" onClick={() => releaseGuarantee.mutate(g.id, {
                              onSuccess: () => showToast({ tone: "success", title: t("bankGuarantees.table.releasedToast") }),
                              onError: (e) => showToast({ tone: "error", title: t("bankGuarantees.table.releaseErrorTitle"), description: getApiErrorMessage(e, t("bankGuarantees.table.releaseErrorFallback")) }),
                            })}>{t("bankGuarantees.table.release")}</Button>
                          ) : null}
                          {canRelease ? (
                            <Button variant="danger" size="sm" onClick={() => { if (window.confirm((t("bankGuarantees.table.markCalledConfirm")))) markCalled.mutate(g.id); }}>{t("bankGuarantees.table.markCalled")}</Button>
                          ) : null}
                        </div>
                      ) : <span className="text-[11px] text-[var(--color-text-muted)]">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        )}
      </Panel>

      {renewing ? <BankGuaranteeRenewDialog projectId={projectId} guarantee={renewing} onClose={() => setRenewing(null)} /> : null}
    </div>
  );
}