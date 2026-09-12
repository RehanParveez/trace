import { Panel, PanelHeader } from "./OrganizationUi";
import {AUDIT_PERMISSIONS, formatAuditAction, formatAuditTimestamp, useAuditLog,
} from "../../audit";
import { usePermissionKeys } from "../../identity";
import { useTranslation } from "react-i18next";

export function DashboardActivityFeed() {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(AUDIT_PERMISSIONS.AUDIT_LOG_READ);

  const auditQuery = useAuditLog(canRead ? { limit: 6 } : undefined);

  if (!canRead) {
    return null;
  }

  const entries = auditQuery.data ?? [];

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow={t("dashboard.activity.eyebrow")}
        title={t("dashboard.activity.title")}
        description={t("dashboard.activity.description")}
      />

      {entries.length === 0 ? (
        <div className="px-5 py-8 text-[13px] text-[var(--color-text-secondary)] sm:px-6">
          {t("dashboard.activity.empty")}
        </div>
      ) : (
        <div className="divide-y divide-[var(--color-border)]">
          {entries.map((entry) => (
            <div key={entry.id} className="px-5 py-3.5 sm:px-6">
              <div className="text-[13px] text-[var(--color-text-primary)]">{entry.summary}</div>
              <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">
                {formatAuditAction(entry.action)} · {entry.actor_name ?? entry.actor_email ?? t("dashboard.activity.system")} · {formatAuditTimestamp(entry.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}