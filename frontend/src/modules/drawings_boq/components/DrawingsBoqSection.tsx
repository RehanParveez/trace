import { useEffect, useState } from "react";
import { ErrorState, LoadingState, Panel } from "../../organizations/components/OrganizationUi";
import { useBOQVersions, useDrawings } from "../hooks";
import type { Drawing } from "../types/drawings-boq.types";
import { DRAWINGS_BOQ_PERMISSIONS } from "../permissions";
import { DrawingTable } from "./DrawingTable";
import { DrawingUploadDialog } from "./DrawingUploadDialog";
import { DrawingElementsDialog } from "./DrawingElementsDialog";
import { BOQVersionTabs } from "./BOQVersionTabs";
import { BOQItemTable } from "./BOQItemTable";

interface DrawingsBoqSectionProps {
  projectId: string;
  permissions: string[];
}

export function DrawingsBoqSection({ projectId, permissions }: DrawingsBoqSectionProps) {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewingDrawing, setViewingDrawing] = useState<Drawing | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | undefined>();

  const drawingsQuery = useDrawings(projectId);
  const boqVersionsQuery = useBOQVersions(projectId);

  const canRead = permissions.includes(DRAWINGS_BOQ_PERMISSIONS.DRAWING_READ);
  const canUpload = permissions.includes(DRAWINGS_BOQ_PERMISSIONS.DRAWING_CREATE);
  const canUpdateBOQ = permissions.includes(DRAWINGS_BOQ_PERMISSIONS.BOQ_UPDATE);
  const canApproveBOQ = permissions.includes(DRAWINGS_BOQ_PERMISSIONS.BOQ_APPROVE);

  const boqVersions = boqVersionsQuery.data ?? [];

  useEffect(() => {
    if (!selectedVersionId && boqVersions.length > 0) setSelectedVersionId(boqVersions[0].id);
  }, [boqVersions, selectedVersionId]);

  if (!canRead) return null;

  if (drawingsQuery.isLoading || boqVersionsQuery.isLoading) return <LoadingState label="Loading drawings…" />;

  if (drawingsQuery.isError || boqVersionsQuery.isError) {
    return (
      <ErrorState
        title="We couldn't load drawings for this project"
        onRetry={() => { void drawingsQuery.refetch(); void boqVersionsQuery.refetch(); }}
      />
    );
  }

  return (
    <div className="space-y-5">
      <DrawingTable drawings={drawingsQuery.data ?? []} canUpload={canUpload} onUpload={() => setUploadOpen(true)} onView={setViewingDrawing} />

      {boqVersions.length > 0 ? (
        <Panel className="overflow-hidden">
          <BOQVersionTabs versions={boqVersions} selectedId={selectedVersionId} onSelect={setSelectedVersionId} />
        </Panel>
      ) : null}

      {selectedVersionId ? (
        <BOQItemTable boqVersionId={selectedVersionId} canUpdate={canUpdateBOQ} canApprove={canApproveBOQ} />
      ) : null}

      {uploadOpen ? <DrawingUploadDialog projectId={projectId} onClose={() => setUploadOpen(false)} /> : null}
      {viewingDrawing ? <DrawingElementsDialog drawing={viewingDrawing} onClose={() => setViewingDrawing(null)} /> : null}
    </div>
  );
}