import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, Button, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, TableShell, Toggle, useToast,
} from "../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../identity";
import { ReasonDialog } from "../../components/ReasonDialog";
import { formatCurrency } from "../../utils/drawings-boq.utils";
import { useProjectOverrides, useRevokeOverride } from "../hooks";
import type { ProjectRateOverride } from "../types/pricing.types";
import { OVERRIDE_STATE_LABEL, formatDate, overrideState, overrideStateTone } from "../utils/pricing.utils";
import { OverrideFormDialog } from "./OverrideFormDialog";

interface ProjectRateOverridesPanelProps {
  projectId: string;
  canAdjust: boolean;
}

export function ProjectRateOverridesPanel({ projectId, canAdjust }: ProjectRateOverridesPanelProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const query = useProjectOverrides(projectId, includeRevoked);
  const revoke = useRevokeOverride(projectId);

  const [formOpen, setFormOpen] = useState(false);
  const [revoking, setRevoking] = useState<ProjectRateOverride | null>(null);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  function confirmRevoke(reason: string) {
    if (!revoking) return;
    setRevokeError(null);
    revoke.mutate(
      { overrideId: revoking.id, reason },
      {
        onSuccess: () => {
          showToast({
            tone: "success",
            title: t("pricing.overrides.revokedToast", "Override revoked"),
            description: t("pricing.override.createdDesc", "Run “Price BOQ” again to apply it to the lines."),
          });
          setRevoking(null);
        },
        onError: (e) => setRevokeError(getApiErrorMessage(e, t("pricing.overrides.revokeError", "Couldn't revoke this override."))),
      },
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("pricing.overrides.eyebrow", "PROJECT RATES")}
        title={t("pricing.overrides.title", "Project rate overrides")}
        description={t(
          "pricing.overrides.desc",
          "A rate agreed for this project only. It takes priority over every rate book, needs a reason, and changes the BOQ only when you price it again.",
        )}
        action={
          canAdjust ? (
            <Button variant="primary" size="sm" onClick={() => setFormOpen(true)}>
              {t("pricing.overrides.add", "Add override")}
            </Button>
          ) : null
        }
      />

      <div className="flex items-center gap-3 border-b border-[var(--color-border)] px-5 py-3 text-[12px] text-[var(--color-text-secondary)]">
        <Toggle checked={includeRevoked} onChange={() => setIncludeRevoked((v) => !v)} label={t("pricing.overrides.showRevoked", "Show revoked")} />
        {t("pricing.overrides.showRevoked", "Show revoked")}
      </div>

      {query.isLoading ? (
        <LoadingState label={t("pricing.overrides.loading", "Loading overrides…")} />
      ) : query.isError ? (
        <ErrorState title={t("pricing.overrides.loadError", "We couldn't load the overrides")} onRetry={() => void query.refetch()} />
      ) : query.overrides.length === 0 ? (
        <EmptyState
          icon="key"
          title={t("pricing.overrides.emptyTitle", "No project overrides")}
          description={t("pricing.overrides.emptyDesc", "This project is priced straight from the rate books.")}
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[820px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("pricing.overrides.colItem", "Work item")}</th>
                <th className="px-4 py-3">{t("pricing.overrides.colUnit", "Unit")}</th>
                <th className="px-4 py-3 text-right">{t("pricing.overrides.colRate", "Rate")}</th>
                <th className="px-4 py-3">{t("pricing.overrides.colWindow", "Valid")}</th>
                <th className="px-4 py-3">{t("pricing.overrides.colReason", "Reason")}</th>
                <th className="px-4 py-3">{t("pricing.overrides.colStatus", "Status")}</th>
                {canAdjust ? <th className="px-4 py-3 text-right">{t("pricing.overrides.colActions", "Actions")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {query.overrides.map((o) => {
                const state = overrideState(o);
                return (
                  <tr key={o.id} className={`border-t border-[var(--color-border)] ${state === "revoked" ? "opacity-70" : ""}`}>
                    <td className="px-4 py-3 font-mono text-[12.5px] font-semibold">{o.work_item_code}</td>
                    <td className="px-4 py-3 font-mono text-[12.5px]">{o.unit}</td>
                    <td className="px-4 py-3 text-right font-mono text-[12.5px]">{formatCurrency(o.rate)}</td>
                    <td className="px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
                      {o.effective_from || o.effective_to
                        ? `${o.effective_from ? formatDate(o.effective_from) : "…"} → ${o.effective_to ? formatDate(o.effective_to) : "…"}`
                        : t("pricing.overrides.always", "Always")}
                    </td>
                    <td className="max-w-[280px] px-4 py-3 text-[12.5px] text-[var(--color-text-secondary)]">
                      {o.reason}
                      {o.revoke_reason ? (
                        <div className="mt-1 text-[11.5px] text-[var(--color-danger)]">
                          {t("pricing.overrides.revokedBecause", "Revoked: {{reason}}", { reason: o.revoke_reason })}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={overrideStateTone(state)}>{t(`pricing.overrideState.${state}`, OVERRIDE_STATE_LABEL[state])}</Badge>
                    </td>
                    {canAdjust ? (
                      <td className="px-4 py-3 text-right">
                        {!o.revoked_at ? (
                          <Button variant="ghost" size="sm" onClick={() => { setRevokeError(null); setRevoking(o); }}>
                            {t("pricing.overrides.revoke", "Revoke")}
                          </Button>
                        ) : null}
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      )}

      {query.hasNextPage ? (
        <div className="flex justify-center border-t border-[var(--color-border)] p-4">
          <Button variant="secondary" size="sm" onClick={() => void query.fetchNextPage()} disabled={query.isFetchingNextPage}>
            {query.isFetchingNextPage ? t("common.loading", "Loading…") : t("pricing.loadMore", "Load more")}
          </Button>
        </div>
      ) : null}

      {formOpen ? <OverrideFormDialog projectId={projectId} onClose={() => setFormOpen(false)} /> : null}
      {revoking ? (
        <ReasonDialog
          title={t("pricing.overrides.revokeTitle", "Revoke this override?")}
          description={t("pricing.overrides.revokeDesc", "{{code}} at {{rate}} stops applying the next time the BOQ is priced.", {
            code: revoking.work_item_code, rate: formatCurrency(revoking.rate),
          })}
          label={t("pricing.overrides.revokeReason", "Reason")}
          required
          confirmLabel={t("pricing.overrides.revoke", "Revoke")}
          pending={revoke.isPending}
          error={revokeError}
          onConfirm={confirmRevoke}
          onClose={() => setRevoking(null)}
        />
      ) : null}
    </Panel>
  );
}
