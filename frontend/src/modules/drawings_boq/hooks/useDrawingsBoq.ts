import { useMutation, useQuery, useQueryClient,  useInfiniteQuery } from "@tanstack/react-query";
import { drawingsBoqApi } from "../api/drawings-boq.api";
import {isDrawingInProgress, openBlobInNewTab, triggerBlobDownload,
} from "../utils/drawings-boq.utils";
import type {AdjustmentCreateRequest, BOQCustomItemCreateRequest, BOQItem, BOQItemUpdateRequest, BOQVersion, BOQVersionUpdateRequest, CalculationRunCreateRequest, DeductionType,
  Drawing, DrawingElementFilters, LabourRate, LabourRateCreateRequest, LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryEntry, MaterialLibraryUpdateRequest, ReviewIssueUpdateRequest,
  ReviewStatus, TransitionRequest, DeductionKind, DeductionResponse, LedgerRowResponse, QuantitySolidResponse, BarMarkResponse
} from "../types/drawings-boq.types";

export const drawingsBoqKeys = {
  all: ["drawings-boq"] as const,

  drawings: (projectId: string) =>
    [...drawingsBoqKeys.all, "drawings", projectId] as const,
  elements: (drawingId: string) =>
    [...drawingsBoqKeys.all, "elements", drawingId] as const,
  elementsPage: (
    drawingId: string,
    filters: DrawingElementFilters,
  ) =>
    [...drawingsBoqKeys.all, "elements-page", drawingId, filters] as const,

  levels: (drawingId: string) =>
    [...drawingsBoqKeys.all, "levels", drawingId] as const,
  audit: (drawingId: string) =>
    [...drawingsBoqKeys.all, "audit", drawingId] as const,
  boqVersions: (projectId: string) =>
    [...drawingsBoqKeys.all, "boq-versions", projectId] as const,
  boqItems: (boqVersionId: string) =>
    [...drawingsBoqKeys.all, "boq-items", boqVersionId] as const,
  boqSummary: (boqVersionId: string) =>
    [...drawingsBoqKeys.all, "boq-summary", boqVersionId] as const,
  materialLibrary: () =>
    [...drawingsBoqKeys.all, "material-library"] as const,
  labourRates: () =>
    [...drawingsBoqKeys.all, "labour-rates"] as const,
  runs: (runId: string) =>
    [...drawingsBoqKeys.all, "runs", runId] as const,
  runStages: (runId: string) =>
    [...drawingsBoqKeys.all, "run-stages", runId] as const,
  runSolids: (
    runId: string,
    params: Record<string, unknown>,
  ) =>
    [...drawingsBoqKeys.all, "run-solids", runId, params] as const,
  runLedger: (
    runId: string,
    params: Record<string, unknown>,
  ) =>
    [...drawingsBoqKeys.all, "run-ledger", runId, params] as const,
  runDeductions: (
    runId: string,
    params: Record<string, unknown>,
  ) =>
    [...drawingsBoqKeys.all, "run-deductions", runId, params] as const,
  versionLedger: (
    versionId: string,
    params: Record<string, unknown>,
  ) =>
    [...drawingsBoqKeys.all, "version-ledger", versionId, params] as const,

  issues: (
    projectId: string,
    versionId?: string,
    status?: string,
  ) =>
    [...drawingsBoqKeys.all, "issues", projectId, versionId, status] as const,

  snapshots: (versionId: string) =>
    [...drawingsBoqKeys.all, "snapshots", versionId] as const,
  snapshotItems: (snapshotId: string) =>
    [...drawingsBoqKeys.all, "snapshot-items", snapshotId] as const,
  adjustments: (itemId: string) =>
    [...drawingsBoqKeys.all, "adjustments", itemId] as const,
  trace: (itemId: string) =>
    [...drawingsBoqKeys.all, "trace", itemId] as const,
  boqItemCounts: () =>
    [...drawingsBoqKeys.all, "boq-item-counts"] as const,
  runBarMarks: (runId: string, params: Record<string, unknown>) =>
    [...drawingsBoqKeys.all, "run-bar-marks", runId, params] as const,
  revisions: (drawingId: string) =>
    [...drawingsBoqKeys.all, "revisions", drawingId] as const,
  sourceElements: (itemId: string) =>
    [...drawingsBoqKeys.all, "source-elements", itemId] as const,
};

export function useDrawings(projectId: string) {
  return useQuery({
    queryKey: drawingsBoqKeys.drawings(projectId),
    queryFn: () => drawingsBoqApi.listDrawings(projectId),
    enabled: Boolean(projectId),
    refetchInterval: (query) =>
      (query.state.data as Drawing[] | undefined)?.some((drawing) =>
        isDrawingInProgress(drawing.status),
      )
        ? 4000
        : false,
  });
}

export function useDrawingElements(
  drawingId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.elements(drawingId ?? ""),
    queryFn: async () => {
      const result = await drawingsBoqApi.listDrawingElements(
        drawingId as string,
        { limit: 5000 },
      );

      return result.items;
    },
    enabled: Boolean(drawingId),
  });
}

export function useDrawingElementsPage(
  drawingId: string | undefined,
  filters: DrawingElementFilters = {},
) {
  return useQuery({
    queryKey: drawingsBoqKeys.elementsPage(
      drawingId ?? "",
      filters,
    ),
    queryFn: () =>
      drawingsBoqApi.listDrawingElements(
        drawingId as string,
        filters,
      ),
    enabled: Boolean(drawingId),
  });
}

export function useDrawingLevels(
  drawingId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.levels(drawingId ?? ""),
    queryFn: () =>
      drawingsBoqApi.listDrawingLevels(
        drawingId as string,
      ),
    enabled: Boolean(drawingId),
  });
}

export function useDrawingAudit(
  drawingId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.audit(drawingId ?? ""),
    queryFn: () =>
      drawingsBoqApi.getDrawingAudit(
        drawingId as string,
      ),
    enabled: Boolean(drawingId),
  });
}

export function useUploadDrawing(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      idempotencyKey,
    }: {
      file: File;
      idempotencyKey: string;
    }) =>
      drawingsBoqApi.uploadDrawing(
        projectId,
        file,
        idempotencyKey,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.drawings(projectId),
      });
    },
  });
}

export function useDeleteDrawing(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (drawingId: string) =>
      drawingsBoqApi.deleteDrawing(drawingId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.drawings(projectId),
      });
    },
  });
}

export function useViewDrawingFile() {
  return useMutation({
    mutationFn: async (drawingId: string) => {
      const blob = await drawingsBoqApi.getDrawingFile(
        drawingId,
      );

      openBlobInNewTab(blob);
    },
  });
}

export function useSuggestItemsFromPdf(
  projectId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (drawingId: string) =>
      drawingsBoqApi.suggestItemsFromPdf(drawingId),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqVersions(projectId),
      });

      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqItems(
          result.boq_version_id,
        ),
      });
    },
  });
}

export function useBOQVersions(projectId: string) {
  return useQuery({
    queryKey: drawingsBoqKeys.boqVersions(projectId),
    queryFn: () =>
      drawingsBoqApi.listBOQVersions(projectId),
    enabled: Boolean(projectId),
  });
}

export function useCreateBOQVersion(
  projectId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (label: string) =>
      drawingsBoqApi.createBOQVersion(
        projectId,
        label,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqVersions(projectId),
      });
    },
  });
}

export function useBOQItems(
  boqVersionId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.boqItems(
      boqVersionId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.listBOQItems(
        boqVersionId as string,
      ),
    enabled: Boolean(boqVersionId),
  });
}

export function useUpdateBOQItem(
  boqVersionId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      itemId,
      payload,
    }: {
      itemId: string;
      payload: BOQItemUpdateRequest;
    }) =>
      drawingsBoqApi.updateBOQItem(
        itemId,
        payload,
      ),
    onSuccess: (item) => {
      queryClient.setQueryData<BOQItem[]>(
        drawingsBoqKeys.boqItems(boqVersionId),
        (current) =>
          current?.map((existing) =>
            existing.id === item.id
              ? item
              : existing,
          ),
      );

      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqSummary(
          boqVersionId,
        ),
      });
      void queryClient.invalidateQueries({ queryKey: [...drawingsBoqKeys.all, "issues"] });
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.adjustments(item.id) });
      void queryClient.invalidateQueries({ queryKey: drawingsBoqKeys.trace(item.id) });
    },
  });
}

export function useApproveBOQItem(
  boqVersionId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) =>
      drawingsBoqApi.approveBOQItem(itemId),
    onSuccess: (item) => {
      queryClient.setQueryData<BOQItem[]>(
        drawingsBoqKeys.boqItems(boqVersionId),
        (current) =>
          current?.map((existing) =>
            existing.id === item.id
              ? item
              : existing,
          ),
      );

      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqSummary(
          boqVersionId,
        ),
      });
    },
  });
}

export function useMaterialLibrary() {
  return useQuery({
    queryKey: drawingsBoqKeys.materialLibrary(),
    queryFn:
      drawingsBoqApi.listMaterialLibrary,
  });
}

export function useCreateMaterialLibraryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      payload: MaterialLibraryCreateRequest,
    ) =>
      drawingsBoqApi.createMaterialLibraryEntry(
        payload,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.materialLibrary(),
      });
    },
  });
}

export function useUpdateMaterialLibraryEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      entryId,
      payload,
    }: {
      entryId: string;
      payload: MaterialLibraryUpdateRequest;
    }) =>
      drawingsBoqApi.updateMaterialLibraryEntry(
        entryId,
        payload,
      ),
    onSuccess: (entry) => {
      queryClient.setQueryData<
        MaterialLibraryEntry[]
      >(
        drawingsBoqKeys.materialLibrary(),
        (current) =>
          current?.map((existing) =>
            existing.id === entry.id
              ? entry
              : existing,
          ),
      );
    },
  });
}

export function useLabourRates() {
  return useQuery({
    queryKey: drawingsBoqKeys.labourRates(),
    queryFn: drawingsBoqApi.listLabourRates,
  });
}

export function useCreateLabourRate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: LabourRateCreateRequest,
    ) =>
      drawingsBoqApi.createLabourRate(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.labourRates(),
      });
    },
  });
}

export function useUpdateLabourRate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      rateId,
      payload,
    }: {
      rateId: string;
      payload: LabourRateUpdateRequest;
    }) =>
      drawingsBoqApi.updateLabourRate(
        rateId,
        payload,
      ),
    onSuccess: (rate) => {
      queryClient.setQueryData<LabourRate[]>(
        drawingsBoqKeys.labourRates(),
        (current) =>
          current?.map((existing) =>
            existing.id === rate.id
              ? rate
              : existing,
          ),
      );
    },
  });
}

export function useAddCustomBOQItem(
  boqVersionId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: BOQCustomItemCreateRequest,
    ) =>
      drawingsBoqApi.addCustomBOQItem(
        boqVersionId,
        payload,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqItems(
            boqVersionId,
          ),
      });
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqSummary(
            boqVersionId,
          ),
      });
    },
  });
}

export function useUpdateBOQVersion(
  projectId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      boqVersionId,
      payload,
    }: {
      boqVersionId: string;
      payload: BOQVersionUpdateRequest;
    }) =>
      drawingsBoqApi.updateBOQVersion(
        boqVersionId,
        payload,
      ),
    onSuccess: (version) => {
      queryClient.setQueryData<BOQVersion[]>(
        drawingsBoqKeys.boqVersions(projectId),
        (current) =>
          current?.map((existing) =>
            existing.id === version.id
              ? version
              : existing,
          ),
      );
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqSummary(
          version.id,
        ),
      });
    },
  });
}

export function useGenerateLabourItems(
  boqVersionId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      drawingsBoqApi.generateLabourItems(
        boqVersionId,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqItems(
            boqVersionId,
          ),
      });
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqSummary(
            boqVersionId,
          ),
      });
    },
  });
}

export function useBOQSummary(
  boqVersionId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.boqSummary(
      boqVersionId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.getBOQSummary(
        boqVersionId as string,
      ),
    enabled: Boolean(boqVersionId),
  });
}

export function useExportBOQ(
  boqVersionId: string,
  label: string,
) {
  return useMutation({
    mutationFn: async (
      format: "pdf" | "xlsx",
    ) => {
      const blob =
        format === "pdf"
          ? await drawingsBoqApi.exportBOQPdf(
              boqVersionId,
            )
          : await drawingsBoqApi.exportBOQXlsx(
              boqVersionId,
            );

      triggerBlobDownload(
        blob,
        `BOQ-${label.replace(
          /\s+/g,
          "_",
        )}.${format}`,
      );
    },
  });
}

export function useBOQItemCounts(
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey:
      drawingsBoqKeys.boqItemCounts(),
    queryFn:
      drawingsBoqApi.getBOQItemCounts,
    enabled: options?.enabled,
  });
}

export function useDrawingRevisions(
  drawingId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.revisions(
      drawingId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.listDrawingRevisions(
        drawingId as string,
      ),
    enabled: Boolean(drawingId),
  });
}

export function useReviseDrawing(
  projectId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      drawingId,
      file,
      revisionLabel,
    }: {
      drawingId: string;
      file: File;
      revisionLabel: string | null;
    }) =>
      drawingsBoqApi.reviseDrawing(
        drawingId,
        file,
        revisionLabel,
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.drawings(projectId),
      });
    },
  });
}

export function useRunBarMarks(
  runId: string | undefined,
  params: { solid_id?: string | null } = {},
) {
  const query = useInfiniteQuery({
    queryKey: drawingsBoqKeys.runBarMarks(runId ?? "", params),
    queryFn: ({ pageParam }) =>
      drawingsBoqApi.listRunBarMarks(runId as string, {
        ...params,
        after: pageParam,
        limit: 200,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: Boolean(runId),
  });

  return {
    ...query,
    rows: (query.data?.pages.flatMap((p) => p.items) ?? []) as BarMarkResponse[],
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: query.fetchNextPage,
  };
}

export function useBOQItemSourceElements(
  boqItemId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.sourceElements(
      boqItemId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.getBOQItemSourceElements(
        boqItemId as string,
      ),
    enabled: Boolean(boqItemId),
  });
}

export function useStartCalculationRun(
  projectId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: CalculationRunCreateRequest,
    ) =>
      drawingsBoqApi.startCalculationRun(
        projectId,
        payload,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.boqVersions(
          projectId,
        ),
      });
    },
  });
}

export function useCalculationRun(
  runId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.runs(
      runId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.getCalculationRun(
        runId as string,
      ),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status =
        query.state.data?.status;
      if (
        status === "QUEUED" ||
        status === "RUNNING" ||
        status === "STAGED" ||
        status === "PROMOTED"
      ) {
        return 2500;
      }
      return false;
    },
  });
}

export function useCalculationRunStages(
  runId: string | undefined,
) {
  return useQuery({
    queryKey:
      drawingsBoqKeys.runStages(
        runId ?? "",
      ),
    queryFn: () =>
      drawingsBoqApi.listCalculationRunStages(
        runId as string,
      ),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const stages = query.state.data;

      if (
        stages?.some(
          (stage) =>
            stage.status === "PENDING" ||
            stage.status === "RUNNING",
        )
      ) {
        return 2500;
      }

      return false;
    },
  });
}

export function useCalculationRunSolids(
  runId: string | undefined,
  params: {
    limit?: number;
    after?: string | null;
    role?: string | null;
    level_id?: string | null;
  } = {},
) {
  return useQuery({
    queryKey: drawingsBoqKeys.runSolids(
      runId ?? "",
      params,
    ),
    queryFn: () =>
      drawingsBoqApi.listRunSolids(
        runId as string,
        params,
      ),
    enabled: Boolean(runId),
  });
}

export function useCalculationRunLedger(
  runId: string | undefined,
  params: {
    limit?: number;
    after?: string | null;
    work_item_code?: string | null;
    level_id?: string | null;
  } = {},
) {
  return useQuery({
    queryKey: drawingsBoqKeys.runLedger(
      runId ?? "",
      params,
    ),
    queryFn: () =>
      drawingsBoqApi.listRunLedger(
        runId as string,
        params,
      ),
    enabled: Boolean(runId),
  });
}

export function useCalculationRunDeductions(
  runId: string | undefined,
  params: {
    limit?: number;
    after?: string | null;
    from_solid_id?: string | null;
    deduction_type?: DeductionType | null;
  } = {},
) {
  return useQuery({
    queryKey:
      drawingsBoqKeys.runDeductions(
        runId ?? "",
        params,
      ),
    queryFn: () =>
      drawingsBoqApi.listRunDeductions(
        runId as string,
        params,
      ),
    enabled: Boolean(runId),
  });
}

export function useBuildBOQFromCalculationRun(
  projectId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) =>
      drawingsBoqApi.buildBOQFromCalculationRun(
        runId,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqVersions(
            projectId,
          ),
      });

      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.all,
      });
    },
  });
}

function invalidateVersionQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  versionId: string,
  projectId?: string,
) {
  void queryClient.invalidateQueries({
    queryKey:
      drawingsBoqKeys.boqItems(versionId),
  });

  void queryClient.invalidateQueries({
    queryKey:
      drawingsBoqKeys.boqSummary(versionId),
  });

  void queryClient.invalidateQueries({
    queryKey:
      drawingsBoqKeys.snapshots(versionId),
  });

  void queryClient.invalidateQueries({
    queryKey: [...drawingsBoqKeys.all, "issues"],
  });

  void queryClient.invalidateQueries({
    queryKey: [...drawingsBoqKeys.all, "issues"],
  });

  if (projectId) {
    void queryClient.invalidateQueries({
      queryKey:
        drawingsBoqKeys.boqVersions(
          projectId,
        ),
    });
  }
}

export function useSubmitBOQForReview(
  versionId: string,
  projectId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      drawingsBoqApi.submitBOQForReview(
        versionId,
      ),
    onSuccess: (version) => {
      queryClient.setQueryData<BOQVersion[]>(
        projectId
          ? drawingsBoqKeys.boqVersions(
              projectId,
            )
          : ["unused"],
        (current) =>
          current?.map((existing) =>
            existing.id === version.id
              ? version
              : existing,
          ),
      );

      invalidateVersionQueries(
        queryClient,
        versionId,
        projectId,
      );
    },
  });
}

export function useReopenBOQVersion(
  versionId: string,
  projectId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      drawingsBoqApi.reopenBOQVersion(
        versionId,
      ),
    onSuccess: (version) => {
      if (projectId) {
        queryClient.setQueryData<BOQVersion[]>(
          drawingsBoqKeys.boqVersions(
            projectId,
          ),
          (current) =>
            current?.map((existing) =>
              existing.id === version.id
                ? version
                : existing,
            ),
        );
      }

      invalidateVersionQueries(
        queryClient,
        versionId,
        projectId,
      );
    },
  });
}

export function useApproveBOQVersion(
  versionId: string,
  projectId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: TransitionRequest,
    ) =>
      drawingsBoqApi.approveBOQVersion(
        versionId,
        payload,
      ),
    onSuccess: (version) => {
      if (projectId) {
        queryClient.setQueryData<BOQVersion[]>(
          drawingsBoqKeys.boqVersions(
            projectId,
          ),
          (current) =>
            current?.map((existing) =>
              existing.id === version.id
                ? version
                : existing,
            ),
        );
      }

      invalidateVersionQueries(
        queryClient,
        versionId,
        projectId,
      );
    },
  });
}

export function useIssueBOQVersion(
  versionId: string,
  projectId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: TransitionRequest,
    ) =>
      drawingsBoqApi.issueBOQVersion(
        versionId,
        payload,
      ),
    onSuccess: (version) => {
      if (projectId) {
        queryClient.setQueryData<BOQVersion[]>(
          drawingsBoqKeys.boqVersions(
            projectId,
          ),
          (current) =>
            current?.map((existing) =>
              existing.id === version.id
                ? version
                : existing,
            ),
        );
      }

      invalidateVersionQueries(
        queryClient,
        versionId,
        projectId,
      );
    },
  });
}

export function useArchiveBOQVersion(
  versionId: string,
  projectId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      drawingsBoqApi.archiveBOQVersion(
        versionId,
      ),
    onSuccess: (version) => {
      if (projectId) {
        queryClient.setQueryData<BOQVersion[]>(
          drawingsBoqKeys.boqVersions(
            projectId,
          ),
          (current) =>
            current?.map((existing) =>
              existing.id === version.id
                ? version
                : existing,
            ),
        );
      }

      invalidateVersionQueries(
        queryClient,
        versionId,
        projectId,
      );
    },
  });
}

export function useBOQVersionLedger(
  versionId: string | undefined,
  params: {
    limit?: number;
    after?: string | null;
    work_item_code?: string | null;
  } = {},
  isEngine = true,
) {
  return useQuery({
    queryKey:
      drawingsBoqKeys.versionLedger(
        versionId ?? "",
        params,
      ),
    queryFn: () =>
      drawingsBoqApi.listVersionLedger(
        versionId as string,
        params,
      ),
    enabled: Boolean(versionId) && isEngine, 
  });
}

export function useBOQSnapshots(
  versionId: string | undefined,
  isEngine = true,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.snapshots(
      versionId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.listBOQSnapshots(
        versionId as string,
      ),
    enabled: Boolean(versionId) && isEngine, 
  });
}

export function useBOQSnapshotItems(
  snapshotId: string | undefined,
) {
  return useQuery({
    queryKey:
      drawingsBoqKeys.snapshotItems(
        snapshotId ?? "",
      ),
    queryFn: () =>
      drawingsBoqApi.listBOQSnapshotItems(
        snapshotId as string,
      ),
    enabled: Boolean(snapshotId),
  });
}

export function useBOQItemTrace(
  itemId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.trace(
      itemId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.getBOQItemTrace(
        itemId as string,
      ),
    enabled: Boolean(itemId),
  });
}

export function useBOQItemAdjustments(
  itemId: string | undefined,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.adjustments(
      itemId ?? "",
    ),
    queryFn: () =>
      drawingsBoqApi.listBOQItemAdjustments(
        itemId as string,
      ),
    enabled: Boolean(itemId),
  });
}

export function useCreateBOQItemAdjustment(
  itemId: string,
  versionId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: AdjustmentCreateRequest,
    ) =>
      drawingsBoqApi.createBOQItemAdjustment(
        itemId,
        payload,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.adjustments(itemId),
      });

      void queryClient.invalidateQueries({
        queryKey: drawingsBoqKeys.trace(itemId),
      });

      if (versionId) {
        invalidateVersionQueries(
          queryClient,
          versionId,
        );
      }
    },
  });
}

export function useRevokeBOQAdjustment(
  itemId: string,
  versionId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      adjustmentId,
      reason,
    }: {
      adjustmentId: string;
      reason: string;
    }) =>
      drawingsBoqApi.revokeBOQAdjustment(
        adjustmentId,
        { reason },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.adjustments(itemId),
      });

      if (versionId) {
        invalidateVersionQueries(
          queryClient,
          versionId,
        );
      }
    },
  });
}

export function useDeleteBOQItem(versionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => drawingsBoqApi.deleteBOQItem(itemId),
    onSuccess: () => {
      invalidateVersionQueries(queryClient, versionId);
    },
  });
}

export function useWaiveBOQItemReview(
  versionId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      reason,
    }: {
      itemId: string;
      reason: string;
    }) =>
      drawingsBoqApi.waiveBOQItemReview(
        itemId,
        { reason },
      ),
    onSuccess: (item) => {
      queryClient.setQueryData<BOQItem[]>(
        drawingsBoqKeys.boqItems(versionId),
        (current) =>
          current?.map((existing) =>
            existing.id === item.id
              ? item
              : existing,
          ),
      );

      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqSummary(
            versionId,
          ),
      });
    },
  });
}

export function useConfirmBOQItemRate(
  versionId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) =>
      drawingsBoqApi.confirmBOQItemRate(
        itemId,
      ),
    onSuccess: (item) => {
      queryClient.setQueryData<BOQItem[]>(
        drawingsBoqKeys.boqItems(versionId),
        (current) =>
          current?.map((existing) =>
            existing.id === item.id
              ? item
              : existing,
          ),
      );

      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.boqSummary(
            versionId,
          ),
      });
    },
  });
}

export function useReviewIssues(
  projectId: string | undefined,
  versionId?: string,
  status?: ReviewStatus,
) {
  return useQuery({
    queryKey: drawingsBoqKeys.issues(
      projectId ?? "",
      versionId,
      status,
    ),
    queryFn: () =>
      drawingsBoqApi.listReviewIssues(
        projectId as string,
        versionId,
        status,
      ),
    enabled: Boolean(projectId),
  });
}

export function useUpdateReviewIssue(
  projectId: string,
  versionId?: string,
  status?: ReviewStatus,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      issueId,
      payload,
    }: {
      issueId: string;
      payload: ReviewIssueUpdateRequest;
    }) =>
      drawingsBoqApi.updateReviewIssue(
        issueId,
        payload,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey:
          drawingsBoqKeys.issues(
            projectId,
            versionId,
            status,
          ),
      });
      void queryClient.invalidateQueries({
        queryKey: [...drawingsBoqKeys.all, "issues", projectId],
      });
    },
  });
}

export function useExportAdvancedBOQ(
  versionId: string,
  label: string,
) {
  return useMutation({
    mutationFn: async ({
      kind,
      format,
      snapshotId,
      compareSnapshotId,
    }: {
      kind:
        | "CONTRACT_BOQ"
        | "PROCUREMENT"
        | "MEASUREMENT_BOOK"
        | "AUDIT_REPORT"
        | "REVISION_COMPARISON"
        | "BBS";
      format: "pdf" | "xlsx";
      snapshotId?: string | null;
      compareSnapshotId?: string | null;
    }) => {
      const blob =
        await drawingsBoqApi.exportAdvancedBOQ(
          versionId,
          kind,
          format,
          snapshotId,
          compareSnapshotId,
        );

      triggerBlobDownload(
        blob,
        `${kind}-${label.replace(/\s+/g, "_")}.${format}`,
      );
    },
  });
}

export function useRunSolids(
  runId: string | undefined,
  params: {
    role?: string | null;
    level_id?: string | null;
  } = {},
) {
  const query = useInfiniteQuery({
    queryKey: drawingsBoqKeys.runSolids(runId ?? "", params),
    queryFn: ({ pageParam }) =>
      drawingsBoqApi.listRunSolids(runId as string, {
        ...params,
        after: pageParam,
        limit: 200,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: Boolean(runId),
  });

  return {
    ...query,
    rows: (query.data?.pages.flatMap((p) => p.items) ?? []) as QuantitySolidResponse[],
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: query.fetchNextPage,
  };
}

export function useRunLedger(
  runId: string | undefined,
  params: {
    work_item_code?: string | null;
    level_id?: string | null;
  } = {},
) {
  const query = useInfiniteQuery({
    queryKey: drawingsBoqKeys.runLedger(runId ?? "", params),
    queryFn: ({ pageParam }) =>
      drawingsBoqApi.listRunLedger(runId as string, {
        ...params,
        after: pageParam,
        limit: 200,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: Boolean(runId),
  });

  return {
    ...query,
    rows: (query.data?.pages.flatMap((p) => p.items) ?? []) as LedgerRowResponse[],
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: query.fetchNextPage,
  };
}

export function useRunDeductions(
  runId: string | undefined,
  params: {
    from_solid_id?: string | null;
    deduction_type?: DeductionKind | null;
  } = {},
) {
  const query = useInfiniteQuery({
    queryKey: drawingsBoqKeys.runDeductions(runId ?? "", params),
    queryFn: ({ pageParam }) =>
      drawingsBoqApi.listRunDeductions(runId as string, {
        ...params,
        after: pageParam,
        limit: 200,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: Boolean(runId),
  });

  return {
    ...query,
    rows: (query.data?.pages.flatMap((p) => p.items) ?? []) as DeductionResponse[],
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: query.fetchNextPage,
  };
}