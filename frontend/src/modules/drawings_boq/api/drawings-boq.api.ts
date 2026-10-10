import { apiClient } from "../../../shared/api/client";
import type {Adjustment, AdjustmentCreateRequest, BOQBuildResponse, BOQCustomItemCreateRequest, BOQItem, BOQItemUpdateRequest, BOQSummary, BOQVersion, BOQVersionUpdateRequest, BuildingLevel,
  CalculationRun, CalculationRunCreateRequest, Drawing, DrawingElement, DrawingElementFilters, LabourRate, LabourRateCreateRequest, LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryEntry,
  MaterialLibraryUpdateRequest, ModelAudit, PDFExtractionResult, ProjectBOQCount, ReasonRequest, ReviewIssue, ReviewIssueUpdateRequest, RunStage, Snapshot, SnapshotItem, TransitionRequest, ItemTrace, 
  DrawingOrganizationSummary, CalculationRunResponse, BOQVersionResponse, TransitionAction, DeductionKind, DeductionResponse, LedgerRowResponse, Page, QuantitySolidResponse,
  BoundaryCandidate, BulkReviewResponse, ConfirmImportResponse, FinishPreviewResponse, LevelOption, RematchResponse, RowDecision, ScheduleFromPdfRequest, ScheduleImportDetailResponse, ScheduleImportResponse, ScheduleKind, 
  ScheduleManualCreateRequest, ScheduleRowCreateRequest, ScheduleRowResponse, ScheduleRowUpdateRequest, SpaceCreateRequest, SpaceDetailResponse, SpaceFinishCreateRequest, SpaceFinishResponse,
   SpaceListFilters, SpaceResponse, SpaceUpdateRequest, BarMarkResponse
} from "../types/drawings-boq.types";

function getNextCursor(response: { headers: Record<string, unknown> }): string | null {
  const value =
    response.headers["x-next-cursor"] ??
    response.headers["X-Next-Cursor"];

  return typeof value === "string" && value.length > 0 ? value : null;
}

async function getPage<T>(
  url: string,
  params: Record<string, unknown>,
): Promise<Page<T>> {
  const response = await apiClient.get<T[]>(url, { params });

  const totalHeader = response.headers["x-total-count"];
  const total = totalHeader === undefined ? NaN : Number(totalHeader);

  return {
    items: response.data,
    nextCursor:
      (response.headers["x-next-cursor"] as string | undefined) ?? null,
    total: Number.isFinite(total) ? total : null,
  };
}

export const drawingsBoqApi = {
  async uploadDrawing(
    projectId: string,
    file: File,
    idempotencyKey: string,
  ): Promise<Drawing> {
    if (!projectId) throw new Error("Project ID is required");
    if (!file) throw new Error("No file selected");
    if (!idempotencyKey) throw new Error("Idempotency key is required");

    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post<Drawing>(
      `/drawings-boq/projects/${projectId}/drawings`,
      formData,
      {
        headers: {
          "Idempotency-Key": idempotencyKey,
          "Content-Type": "multipart/form-data",
        },
      },
    );

    return response.data;
  },

  async listRunBarMarks(runId: string,
   params: { limit?: number; after?: string | null; solid_id?: string | null } = {},
  ): Promise<Page<BarMarkResponse>> {
   if (!runId) throw new Error("Run ID is required");
   return getPage<BarMarkResponse>(
    `/drawings-boq/calculation-runs/${runId}/bar-marks`,
    { limit: 200, ...params },
  );
 },

  async listDrawings(projectId: string): Promise<Drawing[]> {
    if (!projectId) throw new Error("Project ID is required");

    const response = await apiClient.get<Drawing[]>(
      `/drawings-boq/projects/${projectId}/drawings`,
    );

    return response.data;
  },

  async getDrawingOrganizationSummary(): Promise<DrawingOrganizationSummary> {
    const response =
      await apiClient.get<DrawingOrganizationSummary>(
        "/drawings-boq/organization-summary",
      );

    return response.data;
  },

  async getDrawing(drawingId: string): Promise<Drawing> {
    if (!drawingId) throw new Error("Drawing ID is required");

    const response = await apiClient.get<Drawing>(
      `/drawings-boq/drawings/${drawingId}`,
    );

    return response.data;
  },

  async deleteDrawing(drawingId: string): Promise<void> {
    if (!drawingId) throw new Error("Drawing ID is required");
    await apiClient.delete(`/drawings-boq/drawings/${drawingId}`);
  },

  async getDrawingFile(drawingId: string): Promise<Blob> {
    if (!drawingId) throw new Error("Drawing ID is required");

    const response = await apiClient.get(
      `/drawings-boq/drawings/${drawingId}/file`,
      {
        responseType: "blob",
      },
    );

    return response.data;
  },

  async reviseDrawing(
    drawingId: string,
    file: File,
    revisionLabel: string | null,
    idempotencyKey: string,
  ): Promise<Drawing> {
    if (!drawingId) throw new Error("Drawing ID is required");
    if (!file) throw new Error("No file selected");
    if (!idempotencyKey) throw new Error("Idempotency key is required");

    const formData = new FormData();
    formData.append("file", file);

    if (revisionLabel) {
      formData.append("revision_label", revisionLabel);
    }

    const response = await apiClient.post<Drawing>(
      `/drawings-boq/drawings/${drawingId}/revise`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
          "Idempotency-Key": idempotencyKey,
        },
      },
    );

    return response.data;
  },

  async listDrawingRevisions(drawingId: string): Promise<Drawing[]> {
    if (!drawingId) throw new Error("Drawing ID is required");

    const response = await apiClient.get<Drawing[]>(
      `/drawings-boq/drawings/${drawingId}/revisions`,
    );

    return response.data;
  },

  async getDrawingAudit(drawingId: string): Promise<ModelAudit> {
    if (!drawingId) throw new Error("Drawing ID is required");

    const response = await apiClient.get<ModelAudit>(
      `/drawings-boq/drawings/${drawingId}/audit`,
    );

    return response.data;
  },

  async listDrawingElements(
    drawingId: string,
    filters: DrawingElementFilters = {},
  ): Promise<Page<DrawingElement>> {
    if (!drawingId) throw new Error("Drawing ID is required");

    return getPage<DrawingElement>(
      `/drawings-boq/drawings/${drawingId}/elements`,
      {
        limit: filters.limit ?? 1000,
        cursor: filters.cursor ?? undefined,
        structural_role: filters.structural_role ?? undefined,
        discipline: filters.discipline ?? undefined,
        level_id: filters.level_id ?? undefined,
        normalization_status: filters.normalization_status ?? undefined,
        ifc_type: filters.ifc_type ?? undefined,
      },
    );
  },

  async listDrawingLevels(drawingId: string): Promise<BuildingLevel[]> {
    if (!drawingId) throw new Error("Drawing ID is required");

    const response = await apiClient.get<BuildingLevel[]>(
      `/drawings-boq/drawings/${drawingId}/levels`,
    );

    return response.data;
  },

  async suggestItemsFromPdf(drawingId: string): Promise<PDFExtractionResult> {
    if (!drawingId) throw new Error("Drawing ID is required");

    const response = await apiClient.post<PDFExtractionResult>(
      `/drawings-boq/drawings/${drawingId}/suggest-items`,
    );

    return response.data;
  },

  async getBOQItemSourceElements(boqItemId: string): Promise<DrawingElement[]> {
    if (!boqItemId) throw new Error("BOQ Item ID is required");

    const response = await apiClient.get<DrawingElement[]>(
      `/drawings-boq/boq-items/${boqItemId}/source-elements`,
    );

    return response.data;
  },

  async listBOQVersions(projectId: string): Promise<BOQVersion[]> {
    if (!projectId) throw new Error("Project ID is required");

    const response = await apiClient.get<BOQVersion[]>(
      `/drawings-boq/projects/${projectId}/boq-versions`,
    );

    return response.data;
  },

  async createBOQVersion(
    projectId: string,
    label: string,
  ): Promise<BOQVersion> {
    if (!projectId) throw new Error("Project ID is required");
    if (!label) throw new Error("Label is required");

    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/projects/${projectId}/boq-versions`,
      { label },
    );

    return response.data;
  },

  async updateBOQVersion(
    boqVersionId: string,
    payload: BOQVersionUpdateRequest,
  ): Promise<BOQVersion> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.patch<BOQVersion>(
      `/drawings-boq/boq-versions/${boqVersionId}`,
      payload,
    );

    return response.data;
  },

  async getBOQSummary(boqVersionId: string): Promise<BOQSummary> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.get<BOQSummary>(
      `/drawings-boq/boq-versions/${boqVersionId}/summary`,
    );

    return response.data;
  },

  async getBOQItemCounts(): Promise<ProjectBOQCount[]> {
    const response = await apiClient.get<ProjectBOQCount[]>(
      "/drawings-boq/boq-item-counts",
    );

    return response.data;
  },

  async listBOQItems(boqVersionId: string): Promise<BOQItem[]> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.get<BOQItem[]>(
      `/drawings-boq/boq-versions/${boqVersionId}/items`,
    );

    return response.data;
  },

  async updateBOQItem(
    itemId: string,
    payload: BOQItemUpdateRequest,
  ): Promise<BOQItem> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.patch<BOQItem>(
      `/drawings-boq/boq-items/${itemId}`,
      payload,
    );

    return response.data;
  },

  async approveBOQItem(itemId: string): Promise<BOQItem> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-items/${itemId}/approve`,
    );

    return response.data;
  },

  async addCustomBOQItem(
    boqVersionId: string,
    payload: BOQCustomItemCreateRequest,
  ): Promise<BOQItem> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-versions/${boqVersionId}/items`,
      payload,
    );

    return response.data;
  },

  async getBOQItemTrace(itemId: string): Promise<ItemTrace> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.get<ItemTrace>(
      `/drawings-boq/boq-items/${itemId}/trace`,
    );

    return response.data;
  },

  async transition(
    versionId: string,
    action: TransitionAction,
    note?: string | null,
  ): Promise<BOQVersionResponse> {
    if (!versionId) throw new Error("Version ID is required");

    const body =
      action === "approve" || action === "issue"
        ? { note: note ?? null }
        : undefined;

    const response = await apiClient.post<BOQVersionResponse>(
      `/drawings-boq/boq-versions/${versionId}/${action}`,
      body,
    );

    return response.data;
  },

  async submitBOQForReview(versionId: string): Promise<BOQVersion> {
    if (!versionId) throw new Error("Version ID is required");

    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/submit-review`,
    );

    return response.data;
  },

  async reopenBOQVersion(versionId: string): Promise<BOQVersion> {
    if (!versionId) throw new Error("Version ID is required");

    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/reopen`,
    );

    return response.data;
  },

  async approveBOQVersion(
    versionId: string,
    payload: TransitionRequest = {},
  ): Promise<BOQVersion> {
    if (!versionId) throw new Error("Version ID is required");

    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/approve`,
      payload,
    );

    return response.data;
  },

  async issueBOQVersion(
    versionId: string,
    payload: TransitionRequest = {},
  ): Promise<BOQVersion> {
    if (!versionId) throw new Error("Version ID is required");

    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/issue`,
      payload,
    );

    return response.data;
  },

  async archiveBOQVersion(versionId: string): Promise<BOQVersion> {
    if (!versionId) throw new Error("Version ID is required");

    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/archive`,
    );

    return response.data;
  },

  async exportBOQPdf(boqVersionId: string): Promise<Blob> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.get(
      `/drawings-boq/boq-versions/${boqVersionId}/export/pdf`,
      {
        responseType: "blob",
      },
    );

    return response.data;
  },

  async exportBOQXlsx(boqVersionId: string): Promise<Blob> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.get(
      `/drawings-boq/boq-versions/${boqVersionId}/export/xlsx`,
      {
        responseType: "blob",
      },
    );

    return response.data;
  },

  async exportAdvancedBOQ(
   versionId: string,
   kind:
    | "CONTRACT_BOQ"
    | "PROCUREMENT"
    | "MEASUREMENT_BOOK"
    | "AUDIT_REPORT"
    | "REVISION_COMPARISON"
    | "BBS",
   format: "pdf" | "xlsx",
   snapshotId?: string | null,
   compareSnapshotId?: string | null,
  ): Promise<Blob> {
  if (!versionId) throw new Error("Version ID is required");

  const response = await apiClient.get(
    `/drawings-boq/boq-versions/${versionId}/exports/${kind}`,
    {
      params: {
        fmt: format,
        snapshot_id: snapshotId ?? undefined,
        compare_snapshot_id: compareSnapshotId ?? undefined,
      },
      responseType: "blob",
    },
  );

  return response.data;
},
  async startCalculationRun(
    projectId: string,
    body: CalculationRunCreateRequest = {},
  ): Promise<{
    run: CalculationRunResponse;
    reused: boolean;
  }> {
    if (!projectId) throw new Error("Project ID is required");

    const response = await apiClient.post<CalculationRunResponse>(
      `/drawings-boq/projects/${projectId}/calculation-runs`,
      body,
    );

    return {
      run: response.data,
      reused: response.status === 200,
    };
  },

  async getCalculationRun(runId: string): Promise<CalculationRun> {
    if (!runId) throw new Error("Run ID is required");

    const response = await apiClient.get<CalculationRun>(
      `/drawings-boq/calculation-runs/${runId}`,
    );

    return response.data;
  },

  async listCalculationRunStages(runId: string): Promise<RunStage[]> {
    if (!runId) throw new Error("Run ID is required");

    const response = await apiClient.get<RunStage[]>(
      `/drawings-boq/calculation-runs/${runId}/stages`,
    );

    return response.data;
  },

  async buildBOQFromCalculationRun(runId: string): Promise<BOQBuildResponse> {
    if (!runId) throw new Error("Run ID is required");

    const response = await apiClient.post<BOQBuildResponse>(
      `/drawings-boq/calculation-runs/${runId}/boq`,
    );

    return response.data;
  },

  async listRunSolids(
    runId: string,
    params: {
      limit?: number;
      after?: string | null;
      role?: string | null;
      level_id?: string | null;
    } = {},
  ): Promise<Page<QuantitySolidResponse>> {
    if (!runId) throw new Error("Run ID is required");

    return getPage<QuantitySolidResponse>(
      `/drawings-boq/calculation-runs/${runId}/solids`,
      {
        limit: 200,
        ...params,
      },
    );
  },

  async listRunLedger(
    runId: string,
    params: {
      limit?: number;
      after?: string | null;
      work_item_code?: string | null;
      level_id?: string | null;
    } = {},
  ): Promise<Page<LedgerRowResponse>> {
    if (!runId) throw new Error("Run ID is required");

    return getPage<LedgerRowResponse>(
      `/drawings-boq/calculation-runs/${runId}/ledger`,
      {
        limit: 200,
        ...params,
      },
    );
  },

  async listRunDeductions(
    runId: string,
    params: {
      limit?: number;
      after?: string | null;
      from_solid_id?: string | null;
      deduction_type?: DeductionKind | null;
    } = {},
  ): Promise<Page<DeductionResponse>> {
    if (!runId) throw new Error("Run ID is required");

    return getPage<DeductionResponse>(
      `/drawings-boq/calculation-runs/${runId}/deductions`,
      {
        limit: 200,
        ...params,
      },
    );
  },

  async listVersionLedger(
    versionId: string,
    params: {
      limit?: number;
      after?: string | null;
      work_item_code?: string | null;
    } = {},
  ): Promise<Page<LedgerRowResponse>> {
    if (!versionId) throw new Error("Version ID is required");

    return getPage<LedgerRowResponse>(
      `/drawings-boq/boq-versions/${versionId}/ledger`,
      {
        limit: 200,
        ...params,
      },
    );
  },

  async listBOQSnapshots(versionId: string): Promise<Snapshot[]> {
    if (!versionId) throw new Error("Version ID is required");

    const response = await apiClient.get<Snapshot[]>(
      `/drawings-boq/boq-versions/${versionId}/snapshots`,
    );

    return response.data;
  },

  async listBOQSnapshotItems(snapshotId: string): Promise<SnapshotItem[]> {
    if (!snapshotId) throw new Error("Snapshot ID is required");

    const response = await apiClient.get<SnapshotItem[]>(
      `/drawings-boq/boq-snapshots/${snapshotId}/items`,
    );

    return response.data;
  },

  async listBOQItemAdjustments(itemId: string): Promise<Adjustment[]> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.get<Adjustment[]>(
      `/drawings-boq/boq-items/${itemId}/adjustments`,
    );

    return response.data;
  },

  async createBOQItemAdjustment(
    itemId: string,
    payload: AdjustmentCreateRequest,
  ): Promise<Adjustment> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.post<Adjustment>(
      `/drawings-boq/boq-items/${itemId}/adjustments`,
      payload,
    );

    return response.data;
  },

  async revokeBOQAdjustment(
    adjustmentId: string,
    payload: ReasonRequest,
  ): Promise<Adjustment> {
    if (!adjustmentId) throw new Error("Adjustment ID is required");

    const response = await apiClient.post<Adjustment>(
      `/drawings-boq/boq-adjustments/${adjustmentId}/revoke`,
      payload,
    );

    return response.data;
  },

  async waiveBOQItemReview(
    itemId: string,
    payload: ReasonRequest,
  ): Promise<BOQItem> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-items/${itemId}/waive-review`,
      payload,
    );

    return response.data;
  },

  async deleteBOQItem(itemId: string): Promise<void> {
    if (!itemId) throw new Error("Item ID is required");
    await apiClient.delete(`/drawings-boq/boq-items/${itemId}`);
  },

  async confirmBOQItemRate(itemId: string): Promise<BOQItem> {
    if (!itemId) throw new Error("Item ID is required");

    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-items/${itemId}/confirm-rate`,
    );

    return response.data;
  },

  async generateLabourItems(boqVersionId: string): Promise<BOQItem[]> {
    if (!boqVersionId) throw new Error("BOQ Version ID is required");

    const response = await apiClient.post<BOQItem[]>(
      `/drawings-boq/boq-versions/${boqVersionId}/labour/generate`,
    );

    return response.data;
  },

  async listReviewIssues(
    projectId: string,
    versionId?: string,
    status?: "OPEN" | "RESOLVED" | "WAIVED",
  ): Promise<ReviewIssue[]> {
    if (!projectId) throw new Error("Project ID is required");

    const response = await apiClient.get<ReviewIssue[]>(
      "/drawings-boq/review-issues",
      {
        params: {
          project_id: projectId,
          boq_version_id: versionId ?? undefined,
          status: status ?? undefined,
        },
      },
    );

    return response.data;
  },

  async updateReviewIssue(
    issueId: string,
    payload: ReviewIssueUpdateRequest,
  ): Promise<ReviewIssue> {
    if (!issueId) throw new Error("Issue ID is required");

    const response = await apiClient.patch<ReviewIssue>(
      `/drawings-boq/review-issues/${issueId}`,
      payload,
    );

    return response.data;
  },

  async listMaterialLibrary(): Promise<MaterialLibraryEntry[]> {
    const response = await apiClient.get<MaterialLibraryEntry[]>(
      "/drawings-boq/material-library",
    );

    return response.data;
  },

  async createMaterialLibraryEntry(
    payload: MaterialLibraryCreateRequest,
  ): Promise<MaterialLibraryEntry> {
    const response = await apiClient.post<MaterialLibraryEntry>(
      "/drawings-boq/material-library",
      payload,
    );

    return response.data;
  },

  async updateMaterialLibraryEntry(
    entryId: string,
    payload: MaterialLibraryUpdateRequest,
  ): Promise<MaterialLibraryEntry> {
    if (!entryId) throw new Error("Entry ID is required");

    const response = await apiClient.patch<MaterialLibraryEntry>(
      `/drawings-boq/material-library/${entryId}`,
      payload,
    );

    return response.data;
  },

  async listLabourRates(): Promise<LabourRate[]> {
    const response = await apiClient.get<LabourRate[]>(
      "/drawings-boq/labour-rates",
    );

    return response.data;
  },

  async createLabourRate(
    payload: LabourRateCreateRequest,
  ): Promise<LabourRate> {
    const response = await apiClient.post<LabourRate>(
      "/drawings-boq/labour-rates",
      payload,
    );

    return response.data;
  },

  async updateLabourRate(
    rateId: string,
    payload: LabourRateUpdateRequest,
  ): Promise<LabourRate> {
    if (!rateId) throw new Error("Rate ID is required");

    const response = await apiClient.patch<LabourRate>(
      `/drawings-boq/labour-rates/${rateId}`,
      payload,
    );

    return response.data;
  },
};

const B = "/drawings-boq";

export const spacesSchedulesApi = {
 
  async listLevels(drawingId: string) {
    return (
      await apiClient.get<LevelOption[]>(`${B}/drawings/${drawingId}/levels`)
    ).data;
  },
  async listBoundaryCandidates(drawingId: string) {
    return (
      await apiClient.get<BoundaryCandidate[]>(
        `${B}/drawings/${drawingId}/elements`,
        { params: { limit: 5000 } },
      )
    ).data;
  },

  async listSpaces(projectId: string, f: SpaceListFilters) {
    return (
      await apiClient.get<SpaceResponse[]>(
        `${B}/projects/${projectId}/spaces`,
        { params: f },
      )
    ).data;
  },

  async createSpace(projectId: string, body: SpaceCreateRequest) {
    return (
      await apiClient.post<SpaceResponse>(
        `${B}/projects/${projectId}/spaces`,
        body,
      )
    ).data;
  },

  async getSpace(spaceId: string) {
    return (
      await apiClient.get<SpaceDetailResponse>(`${B}/spaces/${spaceId}`)
    ).data;
  },

  async updateSpace(spaceId: string, body: SpaceUpdateRequest) {
    return (
      await apiClient.patch<SpaceResponse>(`${B}/spaces/${spaceId}`, body)
    ).data;
  },

  async deleteSpace(spaceId: string) {
    await apiClient.delete(`${B}/spaces/${spaceId}`);
  },

  async setBoundaries(spaceId: string, elementIds: string[]) {
    return (
      await apiClient.put<{ boundary_count: number }>(
        `${B}/spaces/${spaceId}/boundaries`,
        { element_ids: elementIds },
      )
    ).data;
  },

  async listFinishes(spaceId: string) {
    return (
      await apiClient.get<SpaceFinishResponse[]>(
        `${B}/spaces/${spaceId}/finishes`,
      )
    ).data;
  },
  
  async upsertFinish(spaceId: string, body: SpaceFinishCreateRequest) {
    return (
      await apiClient.post<SpaceFinishResponse>(
        `${B}/spaces/${spaceId}/finishes`,
        body,
      )
    ).data;
  },

  async deleteFinish(finishId: string) {
    await apiClient.delete(`${B}/space-finishes/${finishId}`);
  },

  async previewFinishes(spaceId: string, ruleSetCode?: string) {
    return (
      await apiClient.get<FinishPreviewResponse>(
        `${B}/spaces/${spaceId}/finish-preview`,
        { params: { rule_set_code: ruleSetCode || undefined } },
      )
    ).data;
  },

  async listImports(projectId: string, status?: string) {
    return (
      await apiClient.get<ScheduleImportResponse[]>(
        `${B}/projects/${projectId}/schedule-imports`,
        { params: { status: status || undefined } },
      )
    ).data;
  },

  async importFile(
    projectId: string,
    file: File,
    kind: ScheduleKind,
    notes?: string | null,
  ) {
    const form = new FormData();
    form.append("file", file);
    form.append("schedule_kind", kind);
    if (notes) form.append("notes", notes);
    return (
      await apiClient.post<ScheduleImportResponse>(
        `${B}/projects/${projectId}/schedule-imports/file`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      )
    ).data;
  },

  async importFromPdf(projectId: string, body: ScheduleFromPdfRequest) {
    return (
      await apiClient.post<ScheduleImportResponse>(
        `${B}/projects/${projectId}/schedule-imports/from-pdf`,
        body,
      )
    ).data;
  },

  async createManualImport(
    projectId: string,
    body: ScheduleManualCreateRequest,
  ) {
    return (
      await apiClient.post<ScheduleImportResponse>(
        `${B}/projects/${projectId}/schedule-imports`,
        body,
      )
    ).data;
  },

  async getImport(importId: string) {
    return (
      await apiClient.get<ScheduleImportDetailResponse>(
        `${B}/schedule-imports/${importId}`,
      )
    ).data;
  },

  async addRow(importId: string, body: ScheduleRowCreateRequest) {
    return (
      await apiClient.post<ScheduleRowResponse>(
        `${B}/schedule-imports/${importId}/rows`,
        body,
      )
    ).data;
  },

  async updateRow(rowId: string, body: ScheduleRowUpdateRequest) {
    return (
      await apiClient.patch<ScheduleRowResponse>(
        `${B}/schedule-rows/${rowId}`,
        body,
      )
    ).data;
  },

  async bulkReview(
    importId: string,
    rowIds: string[],
    decision: RowDecision,
  ) {
    return (
      await apiClient.post<BulkReviewResponse>(
        `${B}/schedule-imports/${importId}/rows/bulk-review`,
        { row_ids: rowIds, review_status: decision },
      )
    ).data;
  },

  async confirmImport(importId: string, rejectPending: boolean) {
    return (
      await apiClient.post<ConfirmImportResponse>(
        `${B}/schedule-imports/${importId}/confirm`,
        { reject_pending: rejectPending },
      )
    ).data;
  },

  async rejectImport(importId: string, note?: string | null) {
    return (
      await apiClient.post<ScheduleImportResponse>(
        `${B}/schedule-imports/${importId}/reject`,
        { note: note ?? null },
      )
    ).data;
  },

  async archiveImport(importId: string) {
    return (
      await apiClient.post<ScheduleImportResponse>(
        `${B}/schedule-imports/${importId}/archive`,
      )
    ).data;
  },

  async rematchImport(importId: string) {
    return (
      await apiClient.post<RematchResponse>(
        `${B}/schedule-imports/${importId}/rematch`,
      )
    ).data;
  },
};