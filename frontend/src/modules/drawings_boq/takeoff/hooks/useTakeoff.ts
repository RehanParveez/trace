import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { takeoffApi } from "../api/takeoff.api";
import type { AcceptBody, FloorChoiceBody, FramePlaceBody, ReconcileQuery, CalibrationCreate, DrawingExtractResult, MeasurementCreate, MeasurementUpdate, PrepareResult, RegisterSyncResult, TakeoffSheet } from "../types/takeoff.types";
import { drawingsBoqKeys } from "../../hooks/useDrawingsBoq";

export const takeoffKeys = {
  all: ["takeoff"] as const,
  modes: () => [...takeoffKeys.all, "modes"] as const,
  overview: (drawingId: string) => [...takeoffKeys.all, "overview", drawingId] as const,
  analysis: (sheetId: string, stamp: string) => [...takeoffKeys.all, "analysis", sheetId, stamp] as const,
  vector: (sheetId: string, stamp: string) => [...takeoffKeys.all, "vector", sheetId, stamp] as const,
  tags: (sheetId: string, stamp: string) => [...takeoffKeys.all, "tags", sheetId, stamp] as const,
  shapes: (sheetId: string, stamp: string) => [...takeoffKeys.all, "shapes", sheetId, stamp] as const,
  projectDrawings: (projectId: string) => [...takeoffKeys.all, "project-drawings", projectId] as const,
  reconciliation: (projectId: string) => [...takeoffKeys.all, "reconciliation", projectId] as const,
  facts: (drawingId: string) => [...takeoffKeys.all, "facts", drawingId] as const,
  frame: (drawingId: string) => [...takeoffKeys.all, "frame", drawingId] as const,
  floors: (drawingId: string) => [...takeoffKeys.all, "floors", drawingId] as const,
  floorSources: (drawingId: string) => [...takeoffKeys.all, "floor-sources", drawingId] as const,
  reconcile: (drawingId: string, query: ReconcileQuery) => [...takeoffKeys.all, "reconcile", drawingId, query.model_drawing_id ?? "", query.dx_mm ?? null, query.dy_mm ?? null] as const,
  candidates: (sheetId: string) => [...takeoffKeys.all, "candidates", sheetId] as const,
};

export function useDrawingFacts(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.facts(drawingId ?? ""),
    queryFn: () => takeoffApi.facts(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useTakeoffModes() {
  return useQuery({ queryKey: takeoffKeys.modes(), queryFn: takeoffApi.modes, staleTime: 10 * 60_000 });
}

export function useTakeoffOverview(drawingId: string | undefined) {
  return useQuery({
    queryKey: takeoffKeys.overview(drawingId ?? ""),
    queryFn: () => takeoffApi.overview(drawingId as string),
    enabled: Boolean(drawingId),
  });
}

function useInvalidateOverview(drawingId: string | undefined) {
  const qc = useQueryClient();
  return () => {
    if (drawingId) void qc.invalidateQueries({ queryKey: takeoffKeys.overview(drawingId) });
    void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "project-drawings"] });
    };
}
function useInvalidateRegister(drawingId: string | undefined) {
  const qc = useQueryClient();
  return () => {
    if (!drawingId) return;
    void qc.invalidateQueries({ queryKey: [...drawingsBoqKeys.all, "elements-page", drawingId] });
    void qc.invalidateQueries({ queryKey: drawingsBoqKeys.elements(drawingId) });
  };
}

export function useSyncPdfRegister(drawingId: string | undefined) {
  const invalidate = useInvalidateRegister(drawingId);
  return useMutation({
    mutationFn: () => takeoffApi.syncRegister(drawingId as string),
    onSettled: invalidate,
  });
}

export type ReadStage = "PREPARE" | "READ" | "LIST";
export interface ReadIssue { page_no: number; message: string }
export interface ReadPdfOutcome { register: RegisterSyncResult; issues: ReadIssue[] }

export function useReadPdfDrawing(drawingId: string | undefined) {
  const invalidate = useInvalidateRegister(drawingId);
  const invalidateOverview = useInvalidateOverview(drawingId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { onStage?: (stage: ReadStage) => void } = {}) => {
      const id = drawingId as string;
      args.onStage?.("PREPARE");
      let prep: PrepareResult;
      let guard = 0;
      do {
        prep = await takeoffApi.prepareDrawing(id, { budget_seconds: 45 });
        guard += 1;
      } while (prep.remaining > 0 && prep.prepared.length > 0 && guard < 20);
      const why = new Map<number, string>();
      for (const f of prep.failed) {
        if (f.page_no != null) why.set(f.page_no, f.message ?? "This sheet could not be read.");
      }
      args.onStage?.("READ");
      let out: DrawingExtractResult;
      guard = 0;
      do {
        out = await takeoffApi.extractDrawing(id, { auto_calibrate: true, only_unread: true });
        guard += 1;
      } while (out.skipped.some((s) => s.code === "TIME_BUDGET") && out.done.length > 0 && guard < 8);
      for (const s of out.skipped) {
        if (s.code !== "TIME_BUDGET") why.set(s.page_no, s.message);
      }
      args.onStage?.("LIST");
      const register = await takeoffApi.syncRegister(id);
      const waiting = new Set(register.waiting.map((w) => w.page_no));
      const issues: ReadIssue[] = [...why.entries()]
        .filter(([page]) => waiting.has(page))
        .sort((a, b) => a[0] - b[0])
        .map(([page_no, message]) => ({ page_no, message }));
      return { register, issues } as ReadPdfOutcome;
    },
    onSettled: () => {
      invalidate();
      invalidateOverview();
      if (drawingId) {
        void qc.invalidateQueries({ queryKey: takeoffKeys.facts(drawingId) });
        void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
      }
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
    },
  });
}

export function useSyncTakeoff(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => takeoffApi.sync(drawingId as string),
    onSuccess: (data) => {
      if (drawingId) qc.setQueryData(takeoffKeys.overview(drawingId), data);
    },
  });
}

export function usePrepareSheets(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: async (args: { sheetIds?: string[]; force?: boolean; onProgress?: (r: PrepareResult) => void }) => {
      let last: PrepareResult | null = null;
      let guard = 0;
      do {
        last = await takeoffApi.prepareDrawing(drawingId as string, { sheet_ids: args.sheetIds, force: args.force && guard === 0, budget_seconds: 45 });
        args.onProgress?.(last);
        guard += 1;
      } while (last.remaining > 0 && last.prepared.length > 0 && guard < 200);
      return last;
    },
    onSettled: invalidate,
  });
}

export function usePrepareSheet(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (sheetId: string) => takeoffApi.prepareSheet(sheetId), onSettled: invalidate });
}

export function useUpdateSheet(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (a: { sheetId: string; body: Parameters<typeof takeoffApi.updateSheet>[1] }) => takeoffApi.updateSheet(a.sheetId, a.body),
    onSettled: invalidate,
  });
}

export function sheetStamp(sheet: TakeoffSheet | undefined): string {
  return sheet ? `${sheet.updated_at}|${sheet.prep_status}|${sheet.content_kind}` : "none";
}

export function useSheetAnalysis(sheet: TakeoffSheet | undefined) {
  return useQuery({
    queryKey: takeoffKeys.analysis(sheet?.id ?? "", sheetStamp(sheet)),
    queryFn: () => takeoffApi.analysis(sheet!.id),
    enabled: Boolean(sheet && sheet.prep_status === "READY"),
    staleTime: Infinity,
  });
}

export function useSheetVector(sheet: TakeoffSheet | undefined) {
  return useQuery({
    queryKey: takeoffKeys.vector(sheet?.id ?? "", sheetStamp(sheet)),
    queryFn: () => takeoffApi.vector(sheet!.id, { max_segments: 60000 }),
    enabled: Boolean(sheet && sheet.prep_status === "READY" && sheet.content_kind === "VECTOR"),
    staleTime: Infinity,
    gcTime: 5 * 60_000,
  });
}

export function useSheetTags(sheet: TakeoffSheet | undefined) {
  return useQuery({
    queryKey: takeoffKeys.tags(sheet?.id ?? "", sheetStamp(sheet)),
    queryFn: () => takeoffApi.tags(sheet!.id),
    enabled: Boolean(sheet && sheet.prep_status === "READY"),
    staleTime: 60_000,
  });
}

export function useSheetShapes(sheet: TakeoffSheet | undefined) {
  return useQuery({
    queryKey: takeoffKeys.shapes(sheet?.id ?? "", sheetStamp(sheet)),
    queryFn: () => takeoffApi.shapes(sheet!.id),
    enabled: Boolean(sheet && sheet.prep_status === "READY" && sheet.content_kind === "VECTOR"),
    staleTime: 60_000,
  });
}

export function useAutoCalibrate(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (a: { sheetId: string; use?: "RECOMMENDED" | "DECLARED" | "DIMENSIONS"; include_regions?: boolean }) =>
      takeoffApi.autoCalibrate(a.sheetId, { use: a.use ?? "RECOMMENDED", make_default: true, include_regions: a.include_regions }),
    onSettled: invalidate,
  });
}

export function useCreateCalibration(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (a: { sheetId: string; body: CalibrationCreate }) => takeoffApi.createCalibration(a.sheetId, a.body),
    onSettled: invalidate,
  });
}

export function useUpdateCalibration(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (a: { id: string; body: Record<string, unknown> }) => takeoffApi.updateCalibration(a.id, a.body), onSettled: invalidate });
}

export function useMakeDefaultCalibration(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (id: string) => takeoffApi.makeDefaultCalibration(id), onSettled: invalidate });
}

export function useDeleteCalibration(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (id: string) => takeoffApi.deleteCalibration(id), onSettled: invalidate });
}

export function useCreateMeasurement(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (a: { sheetId: string; body: MeasurementCreate }) => takeoffApi.createMeasurement(a.sheetId, a.body),
    onSettled: invalidate,
  });
}

export function useUpdateMeasurement(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (a: { id: string; body: MeasurementUpdate }) => takeoffApi.updateMeasurement(a.id, a.body), onSettled: invalidate });
}

export function useDeleteMeasurement(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (id: string) => takeoffApi.deleteMeasurement(id), onSettled: invalidate });
}

export function useConfirmMeasurement(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (id: string) => takeoffApi.confirm(id), onSettled: invalidate });
}

export function useUnconfirmMeasurement(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (id: string) => takeoffApi.unconfirm(id), onSettled: invalidate });
}

export function useBulkConfirm(drawingId: string | undefined) {
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({ mutationFn: (ids: string[]) => takeoffApi.bulkConfirm(ids), onSettled: invalidate });
}

export function useProjectTakeoffDrawings(projectId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.projectDrawings(projectId ?? ""),
    queryFn: async () => (await takeoffApi.projectDrawings(projectId as string)).drawings,
    enabled: Boolean(projectId) && enabled,
    staleTime: 15_000,
  });
}

export function useTakeoffReconciliation(projectId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.reconciliation(projectId ?? ""),
    queryFn: () => takeoffApi.reconciliation(projectId as string),
    enabled: Boolean(projectId) && enabled,
  });
}

export function useSheetCandidates(sheet: TakeoffSheet | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.candidates(sheet?.id ?? ""),
    queryFn: () => takeoffApi.candidates(sheet!.id),
    enabled: Boolean(sheet && sheet.prep_status === "READY" && sheet.content_kind !== "RASTER") && enabled,
  });
}

export function useExtractSheet(drawingId: string | undefined) {
  const qc = useQueryClient();
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (a: { sheetId: string; autoCalibrate: boolean }) => takeoffApi.extract(a.sheetId, { auto_calibrate: a.autoCalibrate }),
    onSuccess: (data) => {
      qc.setQueryData(takeoffKeys.candidates(data.sheet_id), data);
      if (data.floors_chosen?.length) void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
    },
    onSettled: () => {
      invalidate();
      if (drawingId) void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
    },
  });
}

export function useAcceptCandidates(drawingId: string | undefined, sheetId: string | undefined) {
  const qc = useQueryClient();
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (body: AcceptBody) => takeoffApi.acceptCandidates(body),
    onSettled: () => {
      invalidate();
      if (sheetId) void qc.invalidateQueries({ queryKey: takeoffKeys.candidates(sheetId) });
    },
  });
}

export function useDecideCandidates(drawingId: string | undefined, sheetId: string | undefined) {
  const qc = useQueryClient();
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (a: { ids: string[]; action: "reject" | "restore" }) => (a.action === "reject" ? takeoffApi.rejectCandidates(a.ids) : takeoffApi.restoreCandidates(a.ids)),
    onSettled: () => {
      invalidate();
      if (sheetId) void qc.invalidateQueries({ queryKey: takeoffKeys.candidates(sheetId) });
    },
  });
}

export function useTakeoffFrame(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.frame(drawingId ?? ""),
    queryFn: () => takeoffApi.frame(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useTakeoffReconcile(drawingId: string | undefined, query: ReconcileQuery, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.reconcile(drawingId ?? "", query),
    queryFn: () => takeoffApi.reconcileColumns(drawingId as string, query),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useTakeoffFloors(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.floors(drawingId ?? ""),
    queryFn: () => takeoffApi.floors(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useTakeoffFloorSources(drawingId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: takeoffKeys.floorSources(drawingId ?? ""),
    queryFn: () => takeoffApi.floorSources(drawingId as string),
    enabled: Boolean(drawingId) && enabled,
  });
}

export function useChooseFloorSources(drawingId: string | undefined) {
  const qc = useQueryClient();
  const invalidate = useInvalidateOverview(drawingId);
  return useMutation({
    mutationFn: (body: FloorChoiceBody) => takeoffApi.chooseFloorSources(drawingId as string, body),
    onSuccess: (data) => { qc.setQueryData(takeoffKeys.floorSources(drawingId ?? ""), data.floors); },
    onSettled: () => {
      invalidate();
      void qc.invalidateQueries({ queryKey: [...takeoffKeys.all, "candidates"] });
      if (drawingId) void qc.invalidateQueries({ queryKey: takeoffKeys.floorSources(drawingId) });
    },
  });
}

export function usePlaceFrameView(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FramePlaceBody) => takeoffApi.placeFrameView(drawingId as string, body),
    onSuccess: (frame) => { qc.setQueryData(takeoffKeys.frame(drawingId ?? ""), frame); },
  });
}

export function useSetFrameReference(drawingId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (view: string) => takeoffApi.setFrameReference(drawingId as string, view),
    onSuccess: (frame) => { qc.setQueryData(takeoffKeys.frame(drawingId ?? ""), frame); },
  });
}

export { drawingsBoqKeys };
