import { apiClient } from "../../../shared/api/client";
import type {Adjustment, AdjustmentCreateRequest, BOQBuildResponse, BOQCustomItemCreateRequest, BOQItem, BOQItemUpdateRequest, BOQSummary, BOQVersion, BOQVersionUpdateRequest, BuildingLevel,
  CalculationRun, CalculationRunCreateRequest, CursorPage, Deduction, Drawing, DrawingElement, DrawingElementFilters, LabourRate, LabourRateCreateRequest, LabourRateUpdateRequest,
  LedgerRow, MaterialLibraryCreateRequest, MaterialLibraryEntry, MaterialLibraryUpdateRequest, ModelAudit, PDFExtractionResult, ProjectBOQCount, QuantitySolid, ReasonRequest,
  ReviewIssue, ReviewIssueUpdateRequest, RunStage, Snapshot, SnapshotItem, TransitionRequest, ItemTrace, DrawingOrganizationSummary,
} from "../types/drawings-boq.types";

function getNextCursor(response: { headers: Record<string, unknown> }): string | null {
  const value =
    response.headers["x-next-cursor"] ??
    response.headers["X-Next-Cursor"];

  return typeof value === "string" && value.length > 0 ? value : null;
}

export const drawingsBoqApi = {
  async uploadDrawing(
    projectId: string,
    file: File,
    idempotencyKey: string,
  ): Promise<Drawing> {
    if (!file) {
      throw new Error("No file selected");
    }

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

  async listDrawings(projectId: string): Promise<Drawing[]> {
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
    const response = await apiClient.get<Drawing>(
      `/drawings-boq/drawings/${drawingId}`,
    );

    return response.data;
  },

  async deleteDrawing(drawingId: string): Promise<void> {
    await apiClient.delete(`/drawings-boq/drawings/${drawingId}`);
  },

  async getDrawingFile(drawingId: string): Promise<Blob> {
    const response = await apiClient.get(
      `/drawings-boq/drawings/${drawingId}/file`,
      {
        responseType: "blob",
      },
    );

    return response.data;
  },

  async suggestItemsFromPdf(
    drawingId: string,
  ): Promise<PDFExtractionResult> {
    const response = await apiClient.post<PDFExtractionResult>(
      `/drawings-boq/drawings/${drawingId}/suggest-items`,
    );

    return response.data;
  },

  async listDrawingElements(
    drawingId: string,
    filters: DrawingElementFilters = {},
  ): Promise<CursorPage<DrawingElement>> {
    const response = await apiClient.get<DrawingElement[]>(
      `/drawings-boq/drawings/${drawingId}/elements`,
      {
        params: {
          limit: filters.limit,
          cursor: filters.cursor ?? undefined,
          structural_role: filters.structural_role ?? undefined,
          discipline: filters.discipline ?? undefined,
          level_id: filters.level_id ?? undefined,
          normalization_status:
            filters.normalization_status ?? undefined,
          ifc_type: filters.ifc_type ?? undefined,
        },
      },
    );

    return {
      items: response.data,
      nextCursor: getNextCursor(response),
    };
  },

  async listDrawingLevels(
    drawingId: string,
  ): Promise<BuildingLevel[]> {
    const response = await apiClient.get<BuildingLevel[]>(
      `/drawings-boq/drawings/${drawingId}/levels`,
    );

    return response.data;
  },

  async getDrawingAudit(
    drawingId: string,
  ): Promise<ModelAudit> {
    const response = await apiClient.get<ModelAudit>(
      `/drawings-boq/drawings/${drawingId}/audit`,
    );

    return response.data;
  },

  async listBOQVersions(
    projectId: string,
  ): Promise<BOQVersion[]> {
    const response = await apiClient.get<BOQVersion[]>(
      `/drawings-boq/projects/${projectId}/boq-versions`,
    );

    return response.data;
  },

  async createBOQVersion(
    projectId: string,
    label: string,
  ): Promise<BOQVersion> {
    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/projects/${projectId}/boq-versions`,
      { label },
    );

    return response.data;
  },

  async listBOQItems(
    boqVersionId: string,
  ): Promise<BOQItem[]> {
    const response = await apiClient.get<BOQItem[]>(
      `/drawings-boq/boq-versions/${boqVersionId}/items`,
    );

    return response.data;
  },

  async updateBOQItem(
    itemId: string,
    payload: BOQItemUpdateRequest,
  ): Promise<BOQItem> {
    const response = await apiClient.patch<BOQItem>(
      `/drawings-boq/boq-items/${itemId}`,
      payload,
    );

    return response.data;
  },

  async approveBOQItem(
    itemId: string,
  ): Promise<BOQItem> {
    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-items/${itemId}/approve`,
    );

    return response.data;
  },

  async addCustomBOQItem(
    boqVersionId: string,
    payload: BOQCustomItemCreateRequest,
  ): Promise<BOQItem> {
    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-versions/${boqVersionId}/items`,
      payload,
    );

    return response.data;
  },

  async updateBOQVersion(
    boqVersionId: string,
    payload: BOQVersionUpdateRequest,
  ): Promise<BOQVersion> {
    const response = await apiClient.patch<BOQVersion>(
      `/drawings-boq/boq-versions/${boqVersionId}`,
      payload,
    );

    return response.data;
  },

  async generateLabourItems(
    boqVersionId: string,
  ): Promise<BOQItem[]> {
    const response = await apiClient.post<BOQItem[]>(
      `/drawings-boq/boq-versions/${boqVersionId}/labour/generate`,
    );

    return response.data;
  },

  async getBOQSummary(
    boqVersionId: string,
  ): Promise<BOQSummary> {
    const response = await apiClient.get<BOQSummary>(
      `/drawings-boq/boq-versions/${boqVersionId}/summary`,
    );

    return response.data;
  },

  async exportBOQPdf(
    boqVersionId: string,
  ): Promise<Blob> {
    const response = await apiClient.get(
      `/drawings-boq/boq-versions/${boqVersionId}/export/pdf`,
      {
        responseType: "blob",
      },
    );

    return response.data;
  },

  async exportBOQXlsx(
    boqVersionId: string,
  ): Promise<Blob> {
    const response = await apiClient.get(
      `/drawings-boq/boq-versions/${boqVersionId}/export/xlsx`,
      {
        responseType: "blob",
      },
    );

    return response.data;
  },

  async getBOQItemCounts(): Promise<ProjectBOQCount[]> {
    const response = await apiClient.get<ProjectBOQCount[]>(
      "/drawings-boq/boq-item-counts",
    );

    return response.data;
  },

  async reviseDrawing(
    drawingId: string,
    file: File,
    revisionLabel: string | null,
    idempotencyKey: string,
  ): Promise<Drawing> {
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

  async listDrawingRevisions(
    drawingId: string,
  ): Promise<Drawing[]> {
    const response = await apiClient.get<Drawing[]>(
      `/drawings-boq/drawings/${drawingId}/revisions`,
    );

    return response.data;
  },

  async getBOQItemSourceElements(
    boqItemId: string,
  ): Promise<DrawingElement[]> {
    const response = await apiClient.get<DrawingElement[]>(
      `/drawings-boq/boq-items/${boqItemId}/source-elements`,
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
    const response = await apiClient.patch<LabourRate>(
      `/drawings-boq/labour-rates/${rateId}`,
      payload,
    );

    return response.data;
  },

  async startCalculationRun(
    projectId: string,
    payload: CalculationRunCreateRequest = {},
  ): Promise<CalculationRun> {
    const response = await apiClient.post<CalculationRun>(
      `/drawings-boq/projects/${projectId}/calculation-runs`,
      payload,
    );

    return response.data;
  },

  async getCalculationRun(
    runId: string,
  ): Promise<CalculationRun> {
    const response = await apiClient.get<CalculationRun>(
      `/drawings-boq/calculation-runs/${runId}`,
    );

    return response.data;
  },

  async listCalculationRunStages(
    runId: string,
  ): Promise<RunStage[]> {
    const response = await apiClient.get<RunStage[]>(
      `/drawings-boq/calculation-runs/${runId}/stages`,
    );

    return response.data;
  },

  async listCalculationRunSolids(
    runId: string,
    params: {
      limit?: number;
      after?: string | null;
      role?: string | null;
      level_id?: string | null;
    } = {},
  ): Promise<CursorPage<QuantitySolid>> {
    const response = await apiClient.get<QuantitySolid[]>(
      `/drawings-boq/calculation-runs/${runId}/solids`,
      {
        params: {
          limit: params.limit,
          after: params.after ?? undefined,
          role: params.role ?? undefined,
          level_id: params.level_id ?? undefined,
        },
      },
    );

    return {
      items: response.data,
      nextCursor: getNextCursor(response),
    };
  },

  async listCalculationRunLedger(
    runId: string,
    params: {
      limit?: number;
      after?: string | null;
      work_item_code?: string | null;
      level_id?: string | null;
    } = {},
  ): Promise<CursorPage<LedgerRow>> {
    const response = await apiClient.get<LedgerRow[]>(
      `/drawings-boq/calculation-runs/${runId}/ledger`,
      {
        params: {
          limit: params.limit,
          after: params.after ?? undefined,
          work_item_code: params.work_item_code ?? undefined,
          level_id: params.level_id ?? undefined,
        },
      },
    );

    return {
      items: response.data,
      nextCursor: getNextCursor(response),
    };
  },

  async listCalculationRunDeductions(
    runId: string,
    params: {
      limit?: number;
      after?: string | null;
      from_solid_id?: string | null;
      deduction_type?: string | null;
    } = {},
  ): Promise<CursorPage<Deduction>> {
    const response = await apiClient.get<Deduction[]>(
      `/drawings-boq/calculation-runs/${runId}/deductions`,
      {
        params: {
          limit: params.limit,
          after: params.after ?? undefined,
          from_solid_id: params.from_solid_id ?? undefined,
          deduction_type: params.deduction_type ?? undefined,
        },
      },
    );

    return {
      items: response.data,
      nextCursor: getNextCursor(response),
    };
  },

  async buildBOQFromCalculationRun(
    runId: string,
  ): Promise<BOQBuildResponse> {
    const response = await apiClient.post<BOQBuildResponse>(
      `/drawings-boq/calculation-runs/${runId}/boq`,
    );

    return response.data;
  },

  async submitBOQForReview(
    versionId: string,
  ): Promise<BOQVersion> {
    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/submit-review`,
    );

    return response.data;
  },

  async reopenBOQVersion(
    versionId: string,
  ): Promise<BOQVersion> {
    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/reopen`,
    );

    return response.data;
  },

  async approveBOQVersion(
    versionId: string,
    payload: TransitionRequest = {},
  ): Promise<BOQVersion> {
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
    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/issue`,
      payload,
    );

    return response.data;
  },

  async archiveBOQVersion(
    versionId: string,
  ): Promise<BOQVersion> {
    const response = await apiClient.post<BOQVersion>(
      `/drawings-boq/boq-versions/${versionId}/archive`,
    );

    return response.data;
  },

  async listBOQSnapshots(
    versionId: string,
  ): Promise<Snapshot[]> {
    const response = await apiClient.get<Snapshot[]>(
      `/drawings-boq/boq-versions/${versionId}/snapshots`,
    );

    return response.data;
  },

  async listBOQSnapshotItems(
    snapshotId: string,
  ): Promise<SnapshotItem[]> {
    const response = await apiClient.get<SnapshotItem[]>(
      `/drawings-boq/boq-snapshots/${snapshotId}/items`,
    );

    return response.data;
  },

  async listBOQVersionLedger(
    versionId: string,
    params: {
      limit?: number;
      after?: string | null;
      work_item_code?: string | null;
    } = {},
  ): Promise<CursorPage<LedgerRow>> {
    const response = await apiClient.get<LedgerRow[]>(
      `/drawings-boq/boq-versions/${versionId}/ledger`,
      {
        params: {
          limit: params.limit,
          after: params.after ?? undefined,
          work_item_code: params.work_item_code ?? undefined,
        },
      },
    );

    return {
      items: response.data,
      nextCursor: getNextCursor(response),
    };
  },

  async getBOQItemTrace(
    itemId: string,
  ): Promise<ItemTrace> {
    const response = await apiClient.get<ItemTrace>(
      `/drawings-boq/boq-items/${itemId}/trace`,
    );

    return response.data;
  },

  async listBOQItemAdjustments(
    itemId: string,
  ): Promise<Adjustment[]> {
    const response = await apiClient.get<Adjustment[]>(
      `/drawings-boq/boq-items/${itemId}/adjustments`,
    );

    return response.data;
  },

  async createBOQItemAdjustment(
    itemId: string,
    payload: AdjustmentCreateRequest,
  ): Promise<Adjustment> {
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
    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-items/${itemId}/waive-review`,
      payload,
    );

    return response.data;
  },

  async confirmBOQItemRate(
    itemId: string,
  ): Promise<BOQItem> {
    const response = await apiClient.post<BOQItem>(
      `/drawings-boq/boq-items/${itemId}/confirm-rate`,
    );

    return response.data;
  },

  async listReviewIssues(
    projectId: string,
    versionId?: string,
    status?: "OPEN" | "RESOLVED" | "WAIVED",
  ): Promise<ReviewIssue[]> {
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
    const response = await apiClient.patch<ReviewIssue>(
      `/drawings-boq/review-issues/${issueId}`,
      payload,
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
  ): Promise<Blob> {
    const response = await apiClient.get(
      `/drawings-boq/boq-versions/${versionId}/exports/${kind}`,
      {
        params: {
          fmt: format,
          snapshot_id: snapshotId ?? undefined,
        },
        responseType: "blob",
      },
    );

    return response.data;
  },
};