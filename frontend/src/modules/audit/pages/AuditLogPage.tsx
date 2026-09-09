import { useState } from "react";
import { ErrorState, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { useAuditLog } from "../hooks";
import type { AuditAction, AuditEntityType } from "../types/audit.types";
import { AUDIT_PERMISSIONS } from "../permissions";
import { AuditLogTable } from "../components/AuditLogTable";

const ENTITY_TYPES: AuditEntityType[] = [
  "ORGANIZATION", "ROLE", "MEMBER", "INVITATION", "SUBSCRIPTION",
  "PROJECT", "BOQ_ITEM", "DRAWING", "PROGRESS_CLAIM", "WHATSAPP_CHANNEL", "MATERIAL_LIBRARY",
];

const ACTIONS: AuditAction[] = ["CREATE", "UPDATE", "DELETE", "APPROVE", "REJECT", "STATUS_CHANGE"];

export function AuditLogPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(AUDIT_PERMISSIONS.AUDIT_LOG_READ);

  const [entityType, setEntityType] = useState<AuditEntityType | "">("");
  const [action, setAction] = useState<AuditAction | "">("");

  const auditQuery = useAuditLog({
    entityType: entityType || undefined,
    action: action || undefined,
  });

  if (!canRead) {
    return <ErrorState title="Audit log unavailable" description="You don't have permission to view this organization's audit log." />;
  }

  if (auditQuery.isLoading) return <LoadingState label="Loading audit log…" />;
  if (auditQuery.isError) return <ErrorState title="Couldn't load the audit log" onRetry={() => void auditQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="Audit log" description="A permanent, unmodifiable record of activity across this organization." />

      <div className="flex flex-wrap gap-2">
        <select
          className="rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-[13px] text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-trace-gold-dark)] focus:ring-2 focus:ring-[var(--color-trace-gold)]/20"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value as AuditEntityType | "")}
        >
          <option value="">All entity types</option>
          {ENTITY_TYPES.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
        </select>

        <select
          className="rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-[13px] text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-trace-gold-dark)] focus:ring-2 focus:ring-[var(--color-trace-gold)]/20"
          value={action}
          onChange={(e) => setAction(e.target.value as AuditAction | "")}
        >
          <option value="">All actions</option>
          {ACTIONS.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}
        </select>
      </div>

      <AuditLogTable entries={auditQuery.data ?? []} />
    </div>
  );
}