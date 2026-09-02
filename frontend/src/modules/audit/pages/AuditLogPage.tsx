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
          className="rounded-[8px] border border-[#e1d5bc] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value as AuditEntityType | "")}
        >
          <option value="">All entity types</option>
          {ENTITY_TYPES.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
        </select>

        <select
          className="rounded-[8px] border border-[#e1d5bc] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
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