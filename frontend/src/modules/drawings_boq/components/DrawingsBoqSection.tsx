import { useEffect, useMemo, useState } from "react";
import {ErrorState, LoadingState, Panel,
} from "../../organizations/components/OrganizationUi";
import {useBOQVersions, useDrawings,
} from "../hooks";
import type { BOQVersion, Drawing,
} from "../types/drawings-boq.types";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import { useQuotaStatus } from "../../subscriptions";
import { DrawingTable } from "./DrawingTable";
import { DrawingUploadDialog } from "./DrawingUploadDialog";
import { DrawingElementsDialog } from "./DrawingElementsDialog";
import { BOQVersionTabs } from "./BOQVersionTabs";
import { BOQItemTable } from "./BOQItemTable";
import { BOQSummaryPanel } from "./BOQSummaryPanel";
import { AddCustomBOQItemDialog } from "./AddCustomBOQItemDialog";
import { BOQVersionMetaDialog } from "./BOQVersionMetaDialog";
import { DrawingAuditPanel } from "./DrawingAuditPanel";
import { CalculationRunPanel } from "./CalculationRunPanel";
import { BOQLifecycleActions } from "./BOQLifecycleActions";
import { BOQReviewIssuesPanel } from "./BOQReviewIssuesPanel";
import { BOQVersionLedgerPanel } from "./BOQVersionLedgerPanel";
import { BOQSnapshotsPanel } from "./BOQSnapshotsPanel";
import { BOQAdvancedExportPanel } from "./BOQAdvancedExportPanel";
import { SpacesSchedulesSection } from "./SpacesSchedulesSection";
import { RebarSummaryPanel } from "../../drawings_boq/rebar/components/RebarSummaryPanel";
import { useTranslation } from "react-i18next";

interface DrawingsBoqSectionProps {
  projectId: string;
}

export function DrawingsBoqSection({
  projectId,
}: DrawingsBoqSectionProps) {
  const { t } =
    useTranslation();

  const permissions =
    usePermissionKeys();

  const [uploadOpen, setUploadOpen] =
    useState(false);

  const [viewingDrawing, setViewingDrawing] =
    useState<Drawing | null>(
      null,
    );

  const [selectedVersionId, setSelectedVersionId] =
    useState<string | undefined>();

  const [addingLineItem, setAddingLineItem] =
    useState(false);

  const [editingDetails, setEditingDetails] =
    useState(false);

  const drawingsQuery = useDrawings(projectId);
  const boqVersionsQuery = useBOQVersions(projectId);

  const canRead = permissions.includes(
      IDENTITY_PERMISSIONS.DRAWING_READ,
    );

  const canUpload = permissions.includes(
      IDENTITY_PERMISSIONS.DRAWING_CREATE,
    );

  const canUpdateBOQ = permissions.includes(
      IDENTITY_PERMISSIONS.BOQ_UPDATE,
    );

  const canApproveBOQ = permissions.includes(
      IDENTITY_PERMISSIONS.BOQ_APPROVE,
    );

  const canCreateItem = permissions.includes(
      IDENTITY_PERMISSIONS.BOQ_ITEM_CREATE,
    );

  const canExport = permissions.includes(
      IDENTITY_PERMISSIONS.BOQ_EXPORT,
    );

  const drawingQuota = useQuotaStatus("drawings");

  const canCalculate = permissions.includes(
      IDENTITY_PERMISSIONS.CALC_RUN,
    );

  const canAdjust = permissions.includes(
      IDENTITY_PERMISSIONS.BOQ_ADJUST,
    );

  const canIssue = permissions.includes(
      IDENTITY_PERMISSIONS.BOQ_ISSUE,
    );

  const canResolveReview = permissions.includes(
      IDENTITY_PERMISSIONS.REVIEW_RESOLVE,
    );

  const boqVersions =
    boqVersionsQuery.data ?? [];

  const parsedDrawings =
    useMemo(
      () =>
        (drawingsQuery.data ?? []).filter(
          (drawing) =>
            drawing.status ===
              "PARSED" &&
            drawing.is_current_revision,
        ),
      [drawingsQuery.data],
    );

  const selectedVersion:
    | BOQVersion
    | undefined =
    boqVersions.find(
      (version) =>
        version.id ===
        selectedVersionId,
    );

  useEffect(() => {
    if (
      !selectedVersionId &&
      boqVersions.length > 0
    ) {
      setSelectedVersionId(
        boqVersions[0].id,
      );
    }
  }, [
    boqVersions,
    selectedVersionId,
  ]);

  if (!canRead) {
    return null;
  }

  if (
    drawingsQuery.isLoading ||
    boqVersionsQuery.isLoading
  ) {
    return (
      <LoadingState
        label={t(
          "drawings.section.loading",
        )}
      />
    );
  }

  if (
    drawingsQuery.isError ||
    boqVersionsQuery.isError
  ) {
    return (
      <ErrorState
        title={t(
          "drawings.section.loadError",
        )}
        onRetry={() => {
          void drawingsQuery.refetch();
          void boqVersionsQuery.refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-5">
      <DrawingTable
        projectId={projectId}
        drawings={drawingsQuery.data ?? []}
        canUpload={canUpload}
        canSuggestItems={canCreateItem}
        quotaBlocked={drawingQuota.isAtLimit}
        onUpload={() =>
          setUploadOpen(true)
        }
        onView={setViewingDrawing}
        onItemsSuggested={(
          versionId,
        ) =>
          setSelectedVersionId(
            versionId,
          )
        }
      />

      <SpacesSchedulesSection
        projectId={projectId}
        drawings={drawingsQuery.data ?? []}
      />

      {viewingDrawing ? (
        <div className="space-y-5">
          <DrawingAuditPanel
            drawingId={
              viewingDrawing.id
            }
          />
        </div>
      ) : null}

      {boqVersions.length > 0 ? (
        <Panel className="overflow-hidden">
          <BOQVersionTabs
            versions={boqVersions}
            selectedId={
              selectedVersionId
            }
            onSelect={
              setSelectedVersionId
            }
          />
        </Panel>
      ) : null}

      {selectedVersion ? (
        <>
          <BOQSummaryPanel
            version={selectedVersion}
            canUpdate={canUpdateBOQ}
            canAddItem={canCreateItem}
            canExport={canExport}
            onEditDetails={() =>
              setEditingDetails(
                true,
              )
            }
            onAddLineItem={() =>
              setAddingLineItem(
                true,
              )
            }
          />

          <BOQLifecycleActions
            projectId={projectId}
            version={selectedVersion}
            canUpdate={canUpdateBOQ}
            canApprove={canApproveBOQ}
            canIssue={canIssue}
          />

          <BOQItemTable
            boqVersionId={selectedVersion.id}
            canUpdate={canUpdateBOQ}
            canApprove={canApproveBOQ}
            canAdjust={canAdjust}
          />

          <BOQReviewIssuesPanel
            projectId={projectId}
            versionId = {selectedVersion.id}
            canResolve = {canResolveReview}
          />

          <BOQVersionLedgerPanel
            versionId={selectedVersion.id}
          />

          {selectedVersion.calculation_run_id ? (
            <RebarSummaryPanel
              versionId={selectedVersion.id}
            />
          ) : null}

          <BOQSnapshotsPanel
            versionId={selectedVersion.id}
          />

          <BOQAdvancedExportPanel
            versionId={
              selectedVersion.id
            }
            label={
              selectedVersion.label
            }
            canExport={
              canExport
            }
          />

          {canCalculate ? (
            <CalculationRunPanel
              projectId={
                projectId
              }
              drawingIds={parsedDrawings.map(
                (drawing) =>
                  drawing.id,
              )}
              activeRunId={
                selectedVersion.calculation_run_id ??
                null
              }
              onBOQBuilt={() => {
                void boqVersionsQuery.refetch();
              }}
            />
          ) : null}
        </>
      ) : (
        <Panel>
          <div className="p-6 text-[12px] text-[var(--color-text-secondary)]">
            No BOQ version exists for this project yet.
          </div>
        </Panel>
      )}

      {uploadOpen ? (
        <DrawingUploadDialog
          projectId={
            projectId
          }
          onClose={() =>
            setUploadOpen(false)
          }
        />
      ) : null}

      {viewingDrawing ? (
        <DrawingElementsDialog
          drawing={
            viewingDrawing
          }
          onClose={() =>
            setViewingDrawing(
              null,
            )
          }
        />
      ) : null}

      {addingLineItem &&
      selectedVersionId ? (
        <AddCustomBOQItemDialog
          boqVersionId={
            selectedVersionId
          }
          onClose={() =>
            setAddingLineItem(
              false,
            )
          }
        />
      ) : null}

      {editingDetails &&
      selectedVersion ? (
        <BOQVersionMetaDialog
          projectId={
            projectId
          }
          version={
            selectedVersion
          }
          onClose={() =>
            setEditingDetails(
              false,
            )
          }
        />
      ) : null}
    </div>
  );
}
