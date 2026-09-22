import { useState } from "react";
import { Button, ErrorState, Field, inputClass, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { usePermissionKeys } from "../../identity";
import { SUBCONTRACTOR_PERMISSIONS } from "../permissions";
import { useAgreements, useSubcontractors } from "../hooks";
import { SubcontractorRegistryPanel } from "../components/SubcontractorRegistryPanel";
import { AgreementForm } from "../components/AgreementForm";
import { AgreementCard } from "../components/AgreementCard";
import { AgreementDetailPanel } from "../components/AgreementDetailPanel";
import type { SubcontractAgreementDetail } from "../types/subcontractor.types";

export function SubcontractorsPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(SUBCONTRACTOR_PERMISSIONS.SUBCONTRACTOR_READ);
  const canManage = permissions.includes(SUBCONTRACTOR_PERMISSIONS.SUBCONTRACTOR_MANAGE);
  const canManagePayments = permissions.includes(SUBCONTRACTOR_PERMISSIONS.SUBCONTRACTOR_PAYMENT_MANAGE);

  const projectsQuery = useProjects();
  const subsQuery = useSubcontractors();
  const [projectId, setProjectId] = useState("");
  const [agreementFormOpen, setAgreementFormOpen] = useState(false);
  const [viewingAgreement, setViewingAgreement] = useState<SubcontractAgreementDetail | null>(null);

  const projects = projectsQuery.data ?? [];
  const activeProjectId = projectId || projects[0]?.id || "";
  const agreementsQuery = useAgreements(activeProjectId);

  const subNameById = new Map((subsQuery.data ?? []).map((s) => [s.id, s.name]));
  const subcontractorById = new Map((subsQuery.data ?? []).map((s) => [s.id, s]));

  if (!canRead && permissions.length > 0) {
    return <ErrorState title="Subcontractors unavailable" description="You don't have permission to view subcontractor records." />;
  }
  if (projectsQuery.isLoading) return <LoadingState label="Loading projects…" />;
  if (projectsQuery.isError || !projectsQuery.data) return <ErrorState title="We couldn't load projects" onRetry={() => void projectsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="Subcontractors" description="Trade packages subcontracted out, with running bills, retention and payables tracked per agreement." />

      <SubcontractorRegistryPanel canManage={canManage} />

      {projects.length === 0 ? (
        <ErrorState title="No projects yet" description="Create a project first to subcontract work on it." />
      ) : (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <Field label="Project">
              <select className={inputClass} value={activeProjectId} onChange={(e) => setProjectId(e.target.value)}>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
            {canManage ? <Button variant="primary" onClick={() => setAgreementFormOpen(true)}>New agreement</Button> : null}
          </div>

          {agreementsQuery.isLoading ? (
            <LoadingState label="Loading agreements…" />
          ) : (agreementsQuery.data ?? []).length === 0 ? (
            <ErrorState title="No subcontract agreements yet" description="Create one to start billing a subcontractor for this project." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {(agreementsQuery.data ?? []).map((agreement) => (
                <AgreementCard key={agreement.id} agreement={agreement} subcontractorName={subNameById.get(agreement.subcontractor_id) ?? "—"} onOpen={() => setViewingAgreement(agreement)} />
              ))}
            </div>
          )}

          {agreementFormOpen ? <AgreementForm projectId={activeProjectId} onClose={() => setAgreementFormOpen(false)} /> : null}
          {viewingAgreement ? (
            <AgreementDetailPanel agreement={viewingAgreement} subcontractor={subcontractorById.get(viewingAgreement.subcontractor_id) ?? { is_active_taxpayer: false }} canManage={canManage} canManagePayments={canManagePayments} onClose={() => setViewingAgreement(null)} />
          ) : null}
        </>
      )}
    </div>
  );
}