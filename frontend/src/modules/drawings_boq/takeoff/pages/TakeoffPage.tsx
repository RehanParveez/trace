import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { PDFPageProxy } from "pdfjs-dist";
import { Badge, Button, ErrorState, LoadingState, useToast } from "../../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../../identity";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { takeoffApi } from "../api/takeoff.api";
import { CountsPanel } from "../components/CountsPanel";
import { MeasurePanel } from "../components/MeasurePanel";
import { MeasurementList } from "../components/MeasurementList";
import { PdfSheetViewer } from "../components/PdfSheetViewer";
import type { PointerInfo, ViewerHandle } from "../components/PdfSheetViewer";
import { ResultsPanel } from "../components/ResultsPanel";
import { FramePanel } from "../components/FramePanel";
import { ReconcilePanel } from "../components/ReconcilePanel";
import { shiftQuery } from "../utils/reconcile";
import { useSourceTotals } from "../hooks/useSourceTotals";
import { SourceTotalsPanel } from "../components/SourceTotalsPanel";
import { planBoxes as planBoxesOf } from "../utils/floorSources";
import { FloorLevels } from "../components/FloorLevels";
import { FoundTab } from "../components/FoundTab";
import { ProjectFactsPanel } from "../components/ProjectFactsPanel";
import { ProjectPlansPanel } from "../components/ProjectPlansPanel";
import { candidatePoints } from "../utils/candidates";
import type { TakeoffCandidate } from "../types/takeoff.types";
import { ScalePanel } from "../components/ScalePanel";
import { CompanyConventionsPanel } from "../components/CompanyConventionsPanel";
import type { CaptureState } from "../components/ScalePanel";
import { SheetStrip } from "../components/SheetStrip";
import { SheetIdentityBar } from "../components/SheetIdentityBar";
import { SheetRolePanel } from "../components/SheetRolePanel";
import { AiShadowCard } from "../ai_reader/components/AiShadowCard";
import { sheetTitle } from "../utils/sheetTitle";
import { Toolbar } from "../components/Toolbar";
import { OverlayColourMenu } from "../components/OverlayColourMenu";
import { ReadingGapsBar } from "../components/ReadingGapsBar";
import { useDetailOnly } from "../detail_only/hooks/useDetailOnly";
import { useReadingGaps } from "../hooks/useReadingGaps";
import { detailOnlyMarks } from "../detail_only/utils/detailOnly";
import { readingGapsMarks } from "../utils/readingGaps";
import { markColours } from "../utils/overlayColour";
import type { OverlayMode } from "../utils/overlayColour";
import {takeoffKeys, useAutoCalibrate, useBulkConfirm, useConfirmMeasurement, useCreateCalibration, useCreateMeasurement, useDeleteCalibration, useDeleteMeasurement,
  useMakeDefaultCalibration, usePrepareSheet, usePrepareSheets, useProjectTakeoffDrawings, useSheetAnalysis, useSheetShapes, useSheetTags, useSheetVector,
  useSyncTakeoff, useTakeoffModes, useTakeoffOverview, useTakeoffReconciliation, useTakeoffFrame, useTakeoffFloors, useTakeoffReconcile, useSheetCandidates, usePlaceFrameView, useSetFrameReference, useUnconfirmMeasurement, useUpdateMeasurement,
} from "../hooks/useTakeoff";
import { useLivePreview } from "../hooks/useLivePreview";
import { usePdfDocument } from "../hooks/usePdfDocument";
import { emptyDraft, useTakeoffView } from "../store/takeoffView.store";
import type { Draft, Tool } from "../store/takeoffView.store";
import type {AreaGeometry, CalibrationCreate, Geometry, LengthGeometry, MeasurementCreate, MeasureKind, PickResult, Pt, ReconMode, RegionPick, TakeoffMeasurement, WallPick,
} from "../types/takeoff.types";
import { checkAlignment } from "../utils/alignment";
import type { AlignmentResult, PdfTextItem } from "../utils/alignment";
import { draftGeometry, geometryPoints } from "../utils/draftGeometry";
import { takeoffErrorMessage } from "../utils/errors";
import { bboxOf, dist, orthoConstrain, roundPt } from "../utils/geometry";
import { hitTest } from "../utils/hitTest";
import { DIMENSION_LABEL, emptyForm, formToParams, measurementToForm, modeOption, RESERVED_WORK_ITEMS } from "../utils/measureForm";
import type { MeasureFormValue } from "../utils/measureForm";
import { paintScene } from "../utils/paint";
import type { HoverState, Scene } from "../utils/paint";
import { SnapIndex } from "../utils/snapIndex";
import { pxToPt } from "../utils/viewport";
import type { Matrix, ViewState } from "../utils/viewport";

type Capture = CaptureState;
const NO_CAPTURE: Capture = { target: null, ref: [], check: [] };
const DRAW_TOOLS: Tool[] = ["length", "area", "count", "wall", "room"];
const TABS = ["measure", "list", "scale", "counts", "found", "results", "frame"] as const;

function isTyping(target: EventTarget | null): boolean {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || (target instanceof HTMLElement && target.isContentEditable);
}

export function TakeoffPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { projectId, drawingId } = useParams<{ projectId: string; drawingId: string }>();
  const [search, setSearch] = useSearchParams();
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ);
  const canEditPermission = permissions.includes(IDENTITY_PERMISSIONS.BOQ_UPDATE);
  const canManageCompany = permissions.includes("organization.manage");

  const view = useTakeoffView();
  const { tool, tab, snapOn, snapKinds, showMeasurements, showDimensions, orthoLock, draft, selectedIds, focusId } = view;

  const overview = useTakeoffOverview(drawingId);
  const modes = useTakeoffModes();
  const projectDrawings = useProjectTakeoffDrawings(projectId);
  const sync = useSyncTakeoff(drawingId);
  const prepare = usePrepareSheets(drawingId);
  const prepareOne = usePrepareSheet(drawingId);
  const autoCal = useAutoCalibrate(drawingId);
  const createCal = useCreateCalibration(drawingId);
  const makeDefault = useMakeDefaultCalibration(drawingId);
  const deleteCal = useDeleteCalibration(drawingId);
  const createMeas = useCreateMeasurement(drawingId);
  const updateMeas = useUpdateMeasurement(drawingId);
  const deleteMeas = useDeleteMeasurement(drawingId);
  const confirmMeas = useConfirmMeasurement(drawingId);
  const unconfirmMeas = useUnconfirmMeasurement(drawingId);
  const bulkConfirm = useBulkConfirm(drawingId);

  const sheets = useMemo(() => [...(overview.data?.sheets ?? [])].sort((a, b) => a.page_no - b.page_no), [overview.data]);
  const sheetParam = search.get("sheet");
  const sheet = sheets.find((s) => s.id === sheetParam) ?? sheets[0];
  const sheetId = sheet?.id ?? null;
  const allMeasurements = useMemo(() => overview.data?.measurements ?? [], [overview.data]);
  const calibrations = useMemo(() => (overview.data?.calibrations ?? []).filter((c) => c.sheet_id === sheetId), [overview.data, sheetId]);
  const measurements = useMemo(() => allMeasurements.filter((m) => m.sheet_id === sheetId), [allMeasurements, sheetId]);
  const defaultCal = calibrations.find((c) => c.is_default && c.usable) ?? null;
  const mmPerPt = defaultCal?.mm_per_pt ? Number(defaultCal.mm_per_pt) : null;
  const drawingInfo = projectDrawings.data?.find((d) => d.drawing_id === drawingId);
  const isCurrent = drawingInfo ? drawingInfo.is_current_revision : true;
  const canEdit = canEditPermission && isCurrent;

  const analysis = useSheetAnalysis(sheet);
  const vector = useSheetVector(sheet);
  const tags = useSheetTags(sheet);
  const shapes = useSheetShapes(sheet);
  const recon = useTakeoffReconciliation(projectId, tab === "results");
  const sourceTotals = useSourceTotals(projectId, tab === "results");
  const frame = useTakeoffFrame(drawingId, tab === "frame");
  const floors = useTakeoffFloors(drawingId, tab === "frame");
  const [showPlans, setShowPlans] = useState(true);
  const [colourMode, setColourMode] = useState<OverlayMode>("ITEM");
  const [showReadingGaps, setShowReadingGaps] = useState(false);
  const readingGaps = useReadingGaps(sheet, showReadingGaps);
  const detailOnly = useDetailOnly(drawingId, showReadingGaps);
  const foundOnSheet = useSheetCandidates(sheet, tab === "found" || colourMode !== "ITEM");
  const planBoxes = useMemo(() => (showPlans && tab === "found" ? planBoxesOf(foundOnSheet.data?.extraction.stats) : []), [showPlans, tab, foundOnSheet.data]);
  const [reconcileModel, setReconcileModel] = useState<string | null>(null);
  const [reconcileShift, setReconcileShift] = useState<[string, string]>(["", ""]);
  const reconcile = useTakeoffReconcile(drawingId, shiftQuery(reconcileModel, reconcileShift[0], reconcileShift[1]), tab === "frame");
  const placeFrame = usePlaceFrameView(drawingId);
  const frameRef = useSetFrameReference(drawingId);

  const snapIndex = useMemo(() => (vector.data && vector.data.segments.length ? new SnapIndex(vector.data.segments, vector.data.bbox) : null), [vector.data]);

  const pdf = usePdfDocument(drawingId);
  const [page, setPage] = useState<PDFPageProxy | null>(null);
  const [renderState, setRenderState] = useState<"idle" | "rendering" | "error">("idle");
  useEffect(() => {
    setPage(null);
    if (pdf.status !== "ready" || !sheet) return;
    let cancelled = false;
    pdf.doc
      .getPage(Math.min(Math.max(sheet.page_no, 1), pdf.doc.numPages))
      .then((p) => {
        if (!cancelled) setPage(p);
      })
      .catch(() => {
        if (!cancelled) setRenderState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [pdf, sheet?.id, sheet?.page_no]); 

  const [alignment, setAlignment] = useState<AlignmentResult | null>(null);
  useEffect(() => {
    setAlignment(null);
    if (!page || !sheet || sheet.prep_status !== "READY" || !sheet.text_chars) return;
    let cancelled = false;
    (async () => {
      try {
        const [words, content] = await Promise.all([takeoffApi.text(sheet.id, { mode: "WORD" }), page.getTextContent()]);
        if (cancelled) return;
        const items = content.items.filter((i): i is typeof i & PdfTextItem => "str" in i && Array.isArray((i as { transform?: unknown }).transform)) as unknown as PdfTextItem[];
        setAlignment(checkAlignment(words.words, items));
      } catch {
        if (!cancelled) setAlignment({ state: "UNVERIFIED", checked: 0, matched: 0, maxErrorPt: 0 });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page, sheet?.id, sheet?.updated_at, sheet?.prep_status, sheet?.text_chars]); 
  const misaligned = alignment?.state === "MISALIGNED";

  const syncTried = useRef(false);
  useEffect(() => {
    if (!overview.data || syncTried.current || sheets.length > 0 || !canEditPermission) return;
    syncTried.current = true;
    sync.mutate(undefined, { onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.syncFailed", "This drawing could not be opened for measuring"), description: takeoffErrorMessage(e) }) });
  }, [overview.data, sheets.length, canEditPermission]); 

  const [prepProgress, setPrepProgress] = useState<{ done: number; remaining: number } | null>(null);
  const prepTried = useRef(new Set<string>());
  useEffect(() => {
    if (!canEditPermission || prepare.isPending) return;
    const todo = sheets.filter((s) => (s.prep_status === "PENDING" || (s.prep_status === "READY" && s.stale)) && !prepTried.current.has(s.id));
    if (todo.length === 0) return;
    todo.forEach((s) => prepTried.current.add(s.id));
    let done = 0;
    prepare.mutate(
      { sheetIds: todo.map((s) => s.id), force: todo.some((s) => s.stale), onProgress: (r) => { done += r.prepared.length; setPrepProgress({ done, remaining: r.remaining }); } },
      {
        onSettled: () => setPrepProgress(null),
        onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.prepFailed", "Reading the sheets failed"), description: takeoffErrorMessage(e) }),
      },
    );
  }, [sheets, canEditPermission, prepare.isPending]); 

  const viewerRef = useRef<ViewerHandle>(null);
  const hoverRef = useRef<HoverState | null>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const shiftRef = useRef(false);
  const [form, setForm] = useState<MeasureFormValue>(() => emptyForm("LENGTH"));

  const formKind = useRef<MeasureKind>("LENGTH");
  const lastForms = useRef<Partial<Record<MeasureKind, MeasureFormValue>>>({});
  function formForKind(k: MeasureKind, current: MeasureFormValue): MeasureFormValue {
    if (formKind.current === k) return current;
    lastForms.current[formKind.current] = current;
    formKind.current = k;
    return lastForms.current[k] ?? emptyForm(k);
  }
  const [editing, setEditing] = useState<TakeoffMeasurement | null>(null);
  const [saving, setSaving] = useState(false);
  const [failures, setFailures] = useState<Record<string, string>>({});
  const [capture, setCapture] = useState<Capture>(NO_CAPTURE);
  const [rulerPts, setRulerPts] = useState<Pt[]>([]);
  const [wallPick, setWallPick] = useState<WallPick | null>(null);
  const [regionPick, setRegionPick] = useState<RegionPick | null>(null);
  const [suggestionPts, setSuggestionPts] = useState<Pt[]>([]);
  const [originNote, setOriginNote] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const [deleteMeasTarget, setDeleteMeasTarget] = useState<TakeoffMeasurement | null>(null);
  const [deleteCalTarget, setDeleteCalTarget] = useState<string | null>(null);

  const lastSheet = useRef<string | null>(null);
  const tabRequest = useRef<(typeof TABS)[number] | null>(((t0) => (TABS as readonly string[]).includes(t0 ?? "") ? (t0 as (typeof TABS)[number]) : null)(search.get("tab")));
  useEffect(() => {
    if (!sheetId || lastSheet.current === sheetId) return;
    lastSheet.current = sheetId;
    useTakeoffView.setState({ draft: null, selectedIds: [], focusId: null, tool: "select", showDimensions: false });
    setCapture(NO_CAPTURE);
    setRulerPts([]);
    setWallPick(null);
    setRegionPick(null);
    setSuggestionPts([]);
    setEditing(null);
    setOriginNote(null);
    setFailures({});
    const wanted = tabRequest.current;
    tabRequest.current = null;
    useTakeoffView.setState({ tab: wanted ?? (calibrations.some((c) => c.is_default && c.usable) ? "measure" : "scale") });
  }, [sheetId]); 
  useEffect(() => () => useTakeoffView.getState().reset(), []);

  const readOnlyReason = !canEditPermission
    ? t("boq.takeoff.block.permission", "You can look at this sheet but your role cannot add measurements.")
    : !isCurrent
      ? t("boq.takeoff.block.revision", "This is not the current revision of the drawing, so it is read-only.")
      : null;
  const drawBlock =
    readOnlyReason ??
    (misaligned ? t("boq.takeoff.block.misaligned", "The sheet on screen and the sheet data read by the server do not line up, so measuring is locked.") : null) ??
    (sheet && sheet.prep_status === "PENDING" ? t("boq.takeoff.block.reading", "This sheet is still being read.") : null) ??
    (!defaultCal ? t("boq.takeoff.block.calibrate", "Calibrate this sheet first (Scale tab).") : null);
  const canDraw = drawBlock === null;
  const canPick = canDraw && sheet?.content_kind === "VECTOR" && Boolean(snapIndex);
  const snapAvailable = Boolean(snapIndex) && !misaligned;
  const snapActive = snapOn && snapAvailable;

  useEffect(() => {
    if (!canDraw && DRAW_TOOLS.includes(tool)) view.setTool("select");
  }, [canDraw, tool]); 

  const kind: MeasureKind | null = editing ? editing.kind : draft ? draft.kind : null;
  const modeOpt = kind ? modeOption(modes.data, kind, form.quantity_mode) : undefined;
  const required = modeOpt?.required_params ?? [];
  useEffect(() => {
    if (!kind || editing) return;
    const next = formForKind(kind, form);
    if (next !== form) setForm(next);
  }, [kind, editing]); 
  useEffect(() => {
    if (!kind || editing || !modes.data) return;
    if (!modeOption(modes.data, kind, form.quantity_mode)) setForm((f) => ({ ...f, quantity_mode: "DIRECT" }));
  }, [kind, editing, modes.data, form.quantity_mode]);

  const parsed = useMemo(() => formToParams(form, required), [form, required.join(",")]); 
  const formErrors = useMemo(
    () => [...parsed.errors, ...parsed.missing.map((f) => `${DIMENSION_LABEL[f]} is needed for this way of measuring.`)],
    [parsed],
  );
  const reservedBlock = RESERVED_WORK_ITEMS.includes(form.work_item_code.trim().toUpperCase())
    ? t("boq.takeoff.block.reserved", "Steel items are measured from the model and cannot be used for PDF takeoff.")
    : null;

  const geom = useMemo(() => {
    if (editing) return { geometry: editing.geometry as Geometry, hint: null as string | null };
    if (draft) return draftGeometry(draft);
    return { geometry: null, hint: null as string | null };
  }, [draft, editing]);

  const previewRequest = useMemo(() => {
    if (!sheet || !kind || !geom.geometry || geom.hint || formErrors.length > 0 || !defaultCal || misaligned) return null;
    return {
      sheet_id: sheet.id,
      kind,
      quantity_mode: form.quantity_mode,
      geometry: geom.geometry,
      params: parsed.params,
      calibration_id: editing?.calibration_id ?? defaultCal.id,
      source: draft?.origin?.source ?? editing?.source ?? ("MANUAL" as const),
    };
  }, [sheet, kind, geom, formErrors.length, defaultCal, misaligned, form.quantity_mode, parsed.params, editing, draft?.origin?.source]);
  const preview = useLivePreview(previewRequest);

  const activeRing = (d: Draft | null): Pt[] => (!d ? [] : d.activeHole !== null ? d.holes[d.activeHole] ?? [] : d.points);

  function resolvePoint(info: PointerInfo, useOrtho: boolean): { pt: Pt; snapped: boolean; kind: HoverState["snapKind"] } {
    const ring = activeRing(draft);
    if (useOrtho && ring.length > 0 && (tool === "length" || tool === "area")) {
      return { pt: roundPt(orthoConstrain(ring[ring.length - 1], info.pt)), snapped: false, kind: null };
    }
    if (info.snap) return { pt: roundPt([info.snap.x, info.snap.y]), snapped: true, kind: info.snap.kind };
    return { pt: roundPt(info.pt), snapped: false, kind: null };
  }

  const onHover = useCallback(
    (info: PointerInfo | null) => {
      if (!info) {
        hoverRef.current = null;
        if (statusRef.current) statusRef.current.textContent = "";
        viewerRef.current?.repaint();
        return;
      }
      const r = resolvePoint(info, orthoLock || shiftRef.current);
      hoverRef.current = { pt: r.pt, snapKind: r.kind, snapPt: r.snapped ? r.pt : null };
      if (statusRef.current) statusRef.current.textContent = `${r.pt[0].toFixed(1)}, ${r.pt[1].toFixed(1)} pt${r.kind ? `  ·  ${r.kind.toLowerCase()}` : ""}`;
      viewerRef.current?.repaint();
    },
    [draft, tool, orthoLock, snapActive, snapKinds], 
  );

  function startCapture(target: "ref" | "check" | null) {
    if (target === null || capture.target === target) {
      setCapture((c) => ({ ...c, target: null }));
      view.setTool("select");
      return;
    }
    setCapture((c) => ({ ...c, target, [target]: [] }));
    view.setTool("calibrate");
    view.setTab("scale");
  }

  function clearDrawing() {
    const d = useTakeoffView.getState().draft;
    useTakeoffView.setState({ draft: d && DRAW_TOOLS.includes(useTakeoffView.getState().tool) && d.kind ? emptyDraft(d.kind) : null });
    setWallPick(null);
    setRegionPick(null);
    setSuggestionPts([]);
    setOriginNote(null);
  }

  async function pickShape(info: PointerInfo, which: "wall" | "room") {
    if (!sheet || !defaultCal || picking) return;
    setPicking(true);
    try {
      const zoom = viewerRef.current?.getView().zoom ?? 1;
      const r: PickResult = await takeoffApi.pick(sheet.id, {
        point: roundPt(info.pt),
        radius_pt: Math.min(25, pxToPt(14, zoom)),
        calibration_id: defaultCal.id,
        wall: which === "wall",
        region: which === "room",
        label_radius_pt: 40,
      });
      const label = r.labels?.[0]?.text ?? "";
      if (which === "wall") {
        if (!r.wall) {
          showToast({ tone: "info", title: t("boq.takeoff.pick.noWall", "No wall found there"), description: t("boq.takeoff.pick.noWallHint", "Click directly on a wall line, or use the Length tool.") });
          return;
        }
        const line = (r.wall.centreline && r.wall.centreline.length >= 2 ? r.wall.centreline : r.wall.run).map(roundPt);
        const thickness = r.wall.thickness_mm ?? r.wall.suggested_thickness_mm ?? null;
        const d: Draft = { ...emptyDraft("LENGTH"), points: line, snapped: line.map(() => true), origin: { source: "VECTOR_SNAP", label, wallThicknessMm: thickness } };
        useTakeoffView.setState({ draft: d, tab: "measure" });
        setWallPick(r.wall);
        setRegionPick(null);
        setOriginNote(r.wall.note ?? (r.wall.partner ? t("boq.takeoff.pick.wallBoth", "Centre line between the two wall faces found on the drawing.") : t("boq.takeoff.pick.wallOne", "Only one wall line was found, so its own line is used.")));
        const base = formForKind("LENGTH", form);
        setForm(((f) => {
          const next = { ...f, label: label || f.label };
          if (f.quantity_mode === "DIRECT" || f.quantity_mode === "LENGTH_X_HEIGHT" || f.quantity_mode === "LENGTH_X_HEIGHT_X_THICKNESS") {
            if (thickness) {
              next.quantity_mode = "LENGTH_X_HEIGHT_X_THICKNESS";
              if (!f.dims.thickness_mm) next.dims = { ...f.dims, thickness_mm: String(Math.round(thickness)) };
            } else if (f.quantity_mode === "DIRECT") next.quantity_mode = "LENGTH_X_HEIGHT";
          }
          return next;
        })(base));
      } else {
        if (!r.region) {
          showToast({ tone: "info", title: t("boq.takeoff.pick.noRoom", "No closed room found there"), description: t("boq.takeoff.pick.noRoomHint", "The walls may have a gap. Use the Area tool and click the corners.") });
          return;
        }
        const outer = r.region.outer.map(roundPt);
        const holes = r.region.holes.map((h) => h.ring.map(roundPt));
        const d: Draft = { ...emptyDraft("AREA"), points: outer, snapped: outer.map(() => true), holes, holeSnapped: holes.map((h) => h.map(() => true)), origin: { source: "VECTOR_SNAP", label } };
        useTakeoffView.setState({ draft: d, tab: "measure" });
        setRegionPick(r.region);
        setWallPick(null);
        setOriginNote(t("boq.takeoff.pick.room", "Outline of the closed space found on the drawing. Check it before saving."));
        const base = formForKind("AREA", form);
        setForm({ ...base, label: label || base.label });
      }
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.pick.failed", "Could not pick from the drawing"), description: takeoffErrorMessage(e) });
    } finally {
      setPicking(false);
    }
  }

  const onPick = (info: PointerInfo) => {
    if (misaligned && tool !== "pan") return;
    const zoom = viewerRef.current?.getView().zoom ?? 1;
    if (tool === "select") {
      const id = hitTest(info.pt, pxToPt(9, zoom), measurements);
      useTakeoffView.setState({ selectedIds: id ? [id] : [], focusId: id });
      if (id) view.setTab("list");
      return;
    }
    if (tool === "ruler") {
      const r = resolvePoint(info, false);
      setRulerPts((p) => (p.length >= 2 ? [r.pt] : [...p, r.pt]));
      return;
    }
    if (tool === "calibrate" && capture.target) {
      const r = resolvePoint(info, false);
      const next = [...capture[capture.target], r.pt].slice(0, 2);
      setCapture({ ...capture, [capture.target]: next, target: next.length >= 2 ? null : capture.target });
      if (next.length >= 2) view.setTool("select");
      return;
    }
    if (!canDraw) return;
    if (tool === "wall" || tool === "room") {
      void pickShape(info, tool);
      return;
    }
    if (!draft) return;
    if (tool === "count") {
      const near = draft.points.findIndex((p) => dist(p, info.pt) <= pxToPt(9, zoom));
      if (near >= 0) {
        view.setDraft({ ...draft, points: draft.points.filter((_, i) => i !== near), snapped: draft.snapped.filter((_, i) => i !== near) });
        return;
      }
    }
    const r = resolvePoint(info, orthoLock || shiftRef.current);
    const ring = activeRing(draft);
    if (ring.length > 0 && dist(ring[ring.length - 1], r.pt) < 1e-6) return; 
    view.addPoint(r.pt, r.snapped);
  };

  const onDoubleClick = () => {
    const d = useTakeoffView.getState().draft;
    if (d && d.activeHole !== null) view.finishHole();
  };

  function toCountDraft(points: Pt[], source: "TAG_SCAN" | "VECTOR_SNAP", tag: string | null, label: string, note: string | null) {
    view.setTool("count");
    const d: Draft = { ...emptyDraft("COUNT"), points: points.map(roundPt), snapped: points.map(() => false), origin: { source, tag, label } };
    useTakeoffView.setState({ draft: d, tab: "measure" });
    const base = formForKind("COUNT", form);
    setForm({ ...base, quantity_mode: "DIRECT", tag: tag ?? "", label: label || base.label });
    setOriginNote(note);
    if (points.length) {
      const b = bboxOf(points);
      if (b) viewerRef.current?.focusBox(b);
    }
  }

  async function applyTag(tag: string) {
    if (!sheet) return;
    try {
      const detail = await takeoffApi.tag(sheet.id, tag);
      toCountDraft(detail.suggestion.geometry.points, detail.suggestion.source, detail.tag, detail.suggestion.label, detail.note ?? t("boq.takeoff.counts.fromTag", "Counted from the {{tag}} labels on the sheet. Click a mark to remove one, or click empty space to add one.", { tag }));
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.counts.tagFailed", "Could not count that tag"), description: takeoffErrorMessage(e) });
    }
  }

  function showCandidate(c: TakeoffCandidate) {
    const pts = candidatePoints(c);
    setSuggestionPts(pts);
    const b = bboxOf(pts);
    if (b) viewerRef.current?.focusBox(b);
  }

  function openMeasurementById(mid: string) {
    deepLinked.current = null;
    view.setTab("list");
    setSearch((p) => { const n = new URLSearchParams(p); n.set("m", mid); return n; }, { replace: true });
  }

  async function previewTag(tag: string) {
    if (!sheet) return;
    try {
      const detail = await takeoffApi.tag(sheet.id, tag);
      const pts = detail.points.map((p) => [p.x, p.y] as Pt);
      setSuggestionPts(pts);
      const b = bboxOf(pts);
      if (b) viewerRef.current?.focusBox(b);
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.counts.tagFailed", "Could not count that tag"), description: takeoffErrorMessage(e) });
    }
  }

  async function applyShape(id: string, previewOnly: boolean) {
    if (!sheet) return;
    try {
      const detail = await takeoffApi.shape(sheet.id, id);
      const pts = detail.suggestion.geometry.points;
      if (previewOnly) {
        setSuggestionPts(pts);
        const b = bboxOf(pts);
        if (b) viewerRef.current?.focusBox(b);
      } else {
        toCountDraft(pts, detail.suggestion.source, detail.suggestion.tag, detail.suggestion.label, t("boq.takeoff.counts.fromShape", "Counted from identical shapes found on the sheet. Check the marks before saving."));
      }
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.counts.shapeFailed", "Could not count those shapes"), description: takeoffErrorMessage(e) });
    }
  }

  const afterChange = () => {
    if (projectId) void qc.invalidateQueries({ queryKey: takeoffKeys.reconciliation(projectId) });
  };

  async function resnapOnServer(d: Draft, g: Geometry): Promise<Geometry> {
    if (!sheet || !snapOn || !vector.data?.truncated || orthoLock || d.origin) return g;
    const rings: Pt[][] = d.kind === "LENGTH" ? [(g as LengthGeometry).points.map((p) => [...p] as Pt)] : [(g as AreaGeometry).outer.map((p) => [...p] as Pt), ...(g as AreaGeometry).holes.map((h) => h.map((p) => [...p] as Pt))];
    const flags: boolean[][] = d.kind === "LENGTH" ? [d.snapped] : [d.snapped, ...d.holeSnapped];
    const todo: Array<{ r: number; i: number }> = [];
    rings.forEach((ring, r) => ring.forEach((_, i) => { if (!flags[r]?.[i]) todo.push({ r, i }); }));
    if (todo.length === 0 || todo.length > 500) return g;
    try {
      const zoom = viewerRef.current?.getView().zoom ?? 1;
      const res = await takeoffApi.snap(sheet.id, { points: todo.map(({ r, i }) => rings[r][i]), radius_pt: Math.min(25, pxToPt(12, zoom)), want: snapKinds });
      res.results.forEach((x, k) => {
        if (x.snapped && x.x !== undefined && x.y !== undefined) rings[todo[k].r][todo[k].i] = roundPt([x.x, x.y]);
      });
    } catch {
      return g;
    }
    return d.kind === "LENGTH" ? { points: rings[0], closed: (g as LengthGeometry).closed } : { outer: rings[0], holes: rings.slice(1) };
  }

  async function save(confirmToo: boolean) {
    if (!sheet || saving) return;
    if (formErrors.length > 0 || reservedBlock) return;
    setSaving(true);
    try {
      const common = {
        quantity_mode: form.quantity_mode,
        params: parsed.params,
        work_item_code: form.work_item_code.trim() ? form.work_item_code.trim().toUpperCase() : null,
        label: form.label.trim() || null,
        tag: form.tag.trim() || null,
        material_grade: form.material_grade.trim() || null,
        recon_mode: form.recon_mode,
      };
      if (editing) {
        const saved = await updateMeas.mutateAsync({ id: editing.id, body: common });
        setEditing(null);
        useTakeoffView.setState({ selectedIds: [saved.id] });
        afterChange();
        showToast({ tone: "success", title: t("boq.takeoff.saved", "Changes saved") });
        return;
      }
      if (!draft || !geom.geometry || geom.hint || !defaultCal) return;
      const geometry = await resnapOnServer(draft, geom.geometry);
      const anySnapped = draft.snapped.some(Boolean) || draft.holeSnapped.some((h) => h.some(Boolean));
      const body: MeasurementCreate = {
        kind: draft.kind,
        geometry,
        calibration_id: defaultCal.id,
        level_id: sheet.level_id,
        source: draft.origin?.source ?? (anySnapped ? "VECTOR_SNAP" : "MANUAL"),
        ...common,
      };
      const created = await createMeas.mutateAsync({ sheetId: sheet.id, body });
      let message = t("boq.takeoff.savedDraft", "Saved as a draft");
      if (confirmToo) {
        try {
          await confirmMeas.mutateAsync(created.id);
          message = t("boq.takeoff.savedConfirmed", "Saved and confirmed");
        } catch (e) {
          setFailures((f) => ({ ...f, [created.id]: takeoffErrorMessage(e) }));
          showToast({ tone: "error", title: t("boq.takeoff.confirmFailed", "Saved as a draft, but it could not be confirmed"), description: takeoffErrorMessage(e) });
          message = "";
        }
      }
      if (message) showToast({ tone: "success", title: message });
      afterChange();
      useTakeoffView.setState({ selectedIds: [created.id] });
      setWallPick(null);
      setRegionPick(null);
      setSuggestionPts([]);
      setOriginNote(null);
      const drawing = DRAW_TOOLS.includes(useTakeoffView.getState().tool);
      useTakeoffView.setState({ draft: drawing ? emptyDraft(draft.kind) : null });
      setForm((f) => ({ ...f, label: "", tag: draft.origin?.tag ? "" : f.tag }));
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.saveFailed", "Could not save the measurement"), description: takeoffErrorMessage(e) });
    } finally {
      setSaving(false);
    }
  }

  function cancelDraft() {
    if (editing) {
      setEditing(null);
      return;
    }
    clearDrawing();
  }

  const busy = confirmMeas.isPending || unconfirmMeas.isPending || deleteMeas.isPending || bulkConfirm.isPending;
  async function confirmOne(id: string) {
    try {
      await confirmMeas.mutateAsync(id);
      setFailures((f) => { const n = { ...f }; delete n[id]; return n; });
      afterChange();
    } catch (e) {
      setFailures((f) => ({ ...f, [id]: takeoffErrorMessage(e) }));
    }
  }
  async function unconfirmOne(id: string) {
    try {
      await unconfirmMeas.mutateAsync(id);
      afterChange();
    } catch (e) {
      setFailures((f) => ({ ...f, [id]: takeoffErrorMessage(e) }));
    }
  }
  async function confirmMany(ids: string[]) {
    try {
      const r = await bulkConfirm.mutateAsync(ids);
      const next: Record<string, string> = {};
      for (const f of r.failed) {
        const id = f.id ?? f.measurement_id;
        if (id) next[id] = takeoffErrorMessage({ response: { data: { error: { code: f.code, message: f.message } } } }, f.message ?? "Could not confirm.");
      }
      setFailures(next);
      afterChange();
      showToast({
        tone: r.failed.length ? "info" : "success",
        title: t("boq.takeoff.bulkResult", "{{ok}} confirmed", { ok: r.confirmed.length }),
        description: r.failed.length ? t("boq.takeoff.bulkFailed", "{{n}} could not be confirmed. The reason is shown on each one.", { n: r.failed.length }) : undefined,
      });
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.bulkError", "Could not confirm"), description: takeoffErrorMessage(e) });
    }
  }
  async function doDeleteMeasurement() {
    if (!deleteMeasTarget) return;
    try {
      await deleteMeas.mutateAsync(deleteMeasTarget.id);
      useTakeoffView.setState({ selectedIds: selectedIds.filter((x) => x !== deleteMeasTarget.id) });
      afterChange();
      setDeleteMeasTarget(null);
    } catch (e) {
      showToast({ tone: "error", title: t("boq.takeoff.deleteFailed", "Could not delete"), description: takeoffErrorMessage(e) });
      setDeleteMeasTarget(null);
    }
  }
  function startEdit(m: TakeoffMeasurement) {
    useTakeoffView.setState({ draft: null, selectedIds: [m.id], focusId: m.id, tool: "select", tab: "measure" });
    lastForms.current[formKind.current] = form;
    formKind.current = m.kind;
    setForm(measurementToForm(m));
    setEditing(m);
    setOriginNote(null);
  }

  function calibrationToast(c: { quality_factor: string; warnings: unknown[]; measurements_recomputed?: number; measurements_reverted_to_draft?: number }) {
    const reverted = c.measurements_reverted_to_draft ?? 0;
    showToast({
      tone: reverted ? "info" : "success",
      title: t("boq.takeoff.scale.done", "Scale set"),
      description: [
        t("boq.takeoff.scale.doneFactor", "Quality factor {{f}}.", { f: Number(c.quality_factor).toFixed(2) }),
        c.measurements_recomputed ? t("boq.takeoff.scale.recomputed", "{{n}} measurements recalculated.", { n: c.measurements_recomputed }) : "",
        reverted ? t("boq.takeoff.scale.reverted", "{{n}} confirmed measurements went back to draft; confirm them again.", { n: reverted }) : "",
      ].filter(Boolean).join(" "),
    });
  }
  function runAuto(use: "RECOMMENDED" | "DECLARED" | "DIMENSIONS" | "ROOMS", includeRegions: boolean) {
    if (!sheet) return;
    autoCal.mutate(
      { sheetId: sheet.id, use, include_regions: includeRegions },
      {
        onSuccess: (r) => { calibrationToast(r.calibration); afterChange(); },
        onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.scale.failed", "Could not set the scale"), description: takeoffErrorMessage(e) }),
      },
    );
  }
  function runManual(body: Parameters<React.ComponentProps<typeof ScalePanel>["onManual"]>[0]) {
    if (!sheet) return;
    const payload: CalibrationCreate = {
      method: body.method,
      make_default: true,
      reference: body.ref ?? null,
      scale_text: body.scale_text ?? null,
      check: body.check ?? null,
    };
    createCal.mutate(
      { sheetId: sheet.id, body: payload },
      {
        onSuccess: (c) => { setCapture(NO_CAPTURE); view.setTool("select"); calibrationToast(c); afterChange(); },
        onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.scale.failed", "Could not set the scale"), description: takeoffErrorMessage(e) }),
      },
    );
  }

  const focusMeasurement = useCallback((m: TakeoffMeasurement) => {
    const b = bboxOf(geometryPoints(m));
    if (!b) return;
    const padX = Math.max(30, (b.x1 - b.x0) * 0.15);
    const padY = Math.max(30, (b.y1 - b.y0) * 0.15);
    viewerRef.current?.focusBox({ x0: b.x0 - padX, y0: b.y0 - padY, x1: b.x1 + padX, y1: b.y1 + padY });
  }, []);
  const deepLinked = useRef<string | null>(null);
  useEffect(() => {
    const id = search.get("m");
    if (!id || !page || deepLinked.current === id) return;
    const m = allMeasurements.find((x) => x.id === id);
    if (!m) return;
    if (m.sheet_id !== sheetId) {
      setSearch((p) => { const n = new URLSearchParams(p); n.set("sheet", m.sheet_id); return n; }, { replace: true });
      return;
    }
    deepLinked.current = id;
    useTakeoffView.setState({ selectedIds: [id], focusId: id, tab: "list" });
    focusMeasurement(m);
  }, [search, allMeasurements, sheetId, page, focusMeasurement, setSearch]);

  function selectSheet(id: string) {
    setSearch((p) => { const n = new URLSearchParams(p); n.set("sheet", id); n.delete("m"); return n; }, { replace: true });
  }

  const keyRef = useRef<(e: KeyboardEvent) => void>(() => undefined);
  keyRef.current = (e: KeyboardEvent) => {
    if (e.key === "Shift") { shiftRef.current = e.type === "keydown"; return; }
    if (e.type !== "keydown" || isTyping(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    const d = useTakeoffView.getState().draft;
    switch (key) {
      case "v": view.setTool("select"); break;
      case "r": view.setTool("ruler"); setRulerPts([]); break;
      case "k": if (canEdit) startCapture("ref"); break;
      case "l": if (canDraw) view.setTool("length"); break;
      case "a": if (canDraw) view.setTool("area"); break;
      case "c": if (canDraw) view.setTool("count"); break;
      case "w": if (canPick) view.setTool("wall"); break;
      case "p": if (canPick) view.setTool("room"); break;
      case "h":
        if (tool === "area" && d && d.points.length >= 3 && d.activeHole === null) view.startHole();
        else view.setTool("pan");
        break;
      case "o": view.setOrtho(!orthoLock); break;
      case "s": if (snapAvailable) view.toggleSnap(); break;
      case "f": viewerRef.current?.fit(); break;
      case "=": case "+": viewerRef.current?.zoomBy(1.3); break;
      case "-": viewerRef.current?.zoomBy(1 / 1.3); break;
      case "Backspace": case "Delete": if (d) { e.preventDefault(); view.removeLastPoint(); } break;
      case "Enter":
        if (d && d.activeHole !== null) view.finishHole();
        else if (d && !geom.hint && !editing && canDraw) { e.preventDefault(); void save(false); }
        break;
      case "Escape":
        if (capture.target) startCapture(null);
        else if (d && d.activeHole !== null) view.finishHole();
        else if (d && (d.points.length > 0 || d.origin)) clearDrawing();
        else if (rulerPts.length) setRulerPts([]);
        else if (suggestionPts.length) setSuggestionPts([]);
        else if (editing) setEditing(null);
        else view.setTool("select");
        break;
      default: return;
    }
  };
  useEffect(() => {
    const handler = (e: KeyboardEvent) => keyRef.current(e);
    window.addEventListener("keydown", handler);
    window.addEventListener("keyup", handler);
    return () => {
      window.removeEventListener("keydown", handler);
      window.removeEventListener("keyup", handler);
    };
  }, []);

  const scene: Scene = {
    measurements,
    selectedIds: new Set(selectedIds),
    showMeasurements,
    tool,
    draft: editing ? null : draft,
    hover: hoverRef.current,
    mmPerPt,
    wallPick: tool === "wall" || draft?.origin ? wallPick : null,
    wallTrim: [0, 0],
    regionPick: tool === "room" || draft?.origin ? regionPick : null,
    calibrationPts: capture.target ? capture[capture.target] : capture.ref.length === 2 ? capture.ref : [],
    rulerPts: tool === "ruler" ? rulerPts : capture.target ? [] : capture.check,
    dimensionPairs: showDimensions ? analysis.data?.detected_scale.measured?.pairs ?? null : null,
    suggestionPts,
    focusId,
    markColours: colourMode === "ITEM" ? undefined : markColours(colourMode, foundOnSheet.data?.candidates ?? []),
    readingGaps: showReadingGaps ? [...readingGapsMarks(readingGaps.data), ...detailOnlyMarks(detailOnly.data, sheet?.id)] : undefined,
    disabledNote: misaligned ? t("boq.takeoff.block.misalignedShort", "Sheet display is not aligned: measuring locked") : null,
  };

  const sceneRef = useRef(scene);
  sceneRef.current = scene;
  const paint = useCallback((ctx: CanvasRenderingContext2D, m: Matrix, size: { w: number; h: number }, _v: ViewState) => {
    void _v;
    sceneRef.current.hover = hoverRef.current;
    paintScene(ctx, m, size, sceneRef.current);
  }, []);
  const paintKey = useMemo(
    () => ({}),
    [measurements, selectedIds, showMeasurements, tool, draft, editing, mmPerPt, wallPick, regionPick, capture, rulerPts, showDimensions, analysis.data, suggestionPts, focusId, misaligned, planBoxes, colourMode, foundOnSheet.data, showReadingGaps, readingGaps.data, detailOnly.data],
  );

  useEffect(() => {
    if (!focusId) return;
    const m = measurements.find((x) => x.id === focusId);
    if (m && tab === "list") focusMeasurement(m);
  }, [focusId]); 

  if (!canRead) {
    return <div className="p-8 text-[14px]">{t("boq.takeoff.noAccess", "Your role cannot open drawings.")}</div>;
  }
  if (overview.isLoading || (overview.data && sheets.length === 0 && sync.isPending)) {
    return <div className="p-6"><LoadingState label={t("boq.takeoff.opening", "Opening the drawing…")} /></div>;
  }
  if (overview.isError) {
    return <div className="p-6"><ErrorState title={t("boq.takeoff.openFailed", "This drawing could not be opened for measuring")} description={takeoffErrorMessage(overview.error)} onRetry={() => void overview.refetch()} /></div>;
  }
  if (!sheet) {
    return (
      <div className="p-6">
        <ErrorState
          title={t("boq.takeoff.noSheets", "This drawing has no sheets to measure")}
          description={sync.isError ? takeoffErrorMessage(sync.error) : canEditPermission ? t("boq.takeoff.noSheetsHint", "Only PDF drawings can be measured.") : t("boq.takeoff.noSheetsAsk", "Ask someone who can edit the BOQ to open this drawing once so its sheets are created.")}
        />
      </div>
    );
  }

  const cursor = tool === "pan" ? "grab" : tool === "select" ? "default" : "crosshair";
  const sum = overview.data?.summary;
  const rasterNote = sheet.content_kind === "RASTER" ? t("boq.takeoff.raster", "Scanned sheet: there are no drawing lines to snap to and precision is limited. Calibrate on a long printed dimension and add a check dimension.") : sheet.content_kind === "UNKNOWN" && sheet.prep_status === "READY" ? t("boq.takeoff.unknownKind", "The sheet type could not be told apart. Snapping may be unavailable.") : null;

  return (
    <div className="flex h-dvh flex-col bg-[var(--color-bg,#f6f4ef)]" data-testid="takeoff-page">
      <header className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5">
        <Link to={projectId ? `/app/projects/${projectId}` : "/app/projects"} className="text-[13px] font-semibold text-[var(--color-info)]">← {t("boq.takeoff.back", "Project")}</Link>
        <h1 className="min-w-0 truncate font-[Archivo] text-[15px] font-bold" title={drawingInfo?.original_filename}>{drawingInfo?.original_filename ?? t("boq.takeoff.title", "PDF takeoff")}</h1>
        {drawingInfo?.revision_label ? <Badge tone={isCurrent ? "slate" : "red"}>{drawingInfo.revision_label}{isCurrent ? "" : ` · ${t("boq.takeoff.older", "older")}`}</Badge> : null}
        <span className="text-[12.5px] text-[var(--color-text-secondary)]">{sheetTitle(sheet)}</span>
        {sum ? (
          <span className="ml-auto flex flex-wrap gap-2">
            <Badge tone={sum.calibrated_sheets === sum.sheets ? "green" : "gold"}>{sum.calibrated_sheets}/{sum.sheets} {t("boq.takeoff.calibrated", "sheets with a scale")}</Badge>
            <Badge tone="slate">{sum.draft} {t("boq.takeoff.list.drafts", "Drafts").toLowerCase()}</Badge>
            <Badge tone="green">{sum.confirmed} {t("boq.takeoff.list.confirmed", "Confirmed").toLowerCase()}</Badge>
          </span>
        ) : null}
      </header>

      {readOnlyReason ? <div className="border-b border-[var(--color-border)] bg-[var(--color-info-bg)] px-4 py-1.5 text-[12.5px] text-[var(--color-info)]" data-testid="readonly-banner">{readOnlyReason}</div> : null}
      {prepProgress || prepare.isPending ? <div className="border-b border-[var(--color-border)] bg-[var(--color-warning-bg)] px-4 py-1.5 text-[12.5px]" data-testid="prep-banner">{t("boq.takeoff.reading", "Reading the sheets…")} {prepProgress ? `${prepProgress.done} ${t("boq.takeoff.readDone", "done")}${prepProgress.remaining ? `, ${prepProgress.remaining} ${t("boq.takeoff.readLeft", "to go")}` : ""}` : ""}</div> : null}
      {sheet.prep_status === "PENDING" && !canEditPermission ? <div className="border-b border-[var(--color-border)] bg-[var(--color-warning-bg)] px-4 py-1.5 text-[12.5px]">{t("boq.takeoff.notRead", "This sheet has not been read yet. Someone who can edit the BOQ needs to open it once.")}</div> : null}
      {sheet.prep_status === "FAILED" ? (
        <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-danger-bg)] px-4 py-1.5 text-[12.5px] text-[var(--color-danger)]" data-testid="prep-failed">
          <span>{t("boq.takeoff.prepFailedSheet", "This sheet could not be read automatically. You can still calibrate by hand and draw on it.")} {sheet.prep_error ? `(${sheet.prep_error})` : ""}</span>
          {canEditPermission ? <Button size="sm" disabled={prepareOne.isPending} onClick={() => prepareOne.mutate(sheet.id)}>{t("boq.takeoff.retry", "Read again")}</Button> : null}
        </div>
      ) : null}
      {rasterNote ? <div className="border-b border-[var(--color-border)] bg-[var(--color-warning-bg)] px-4 py-1.5 text-[12.5px]" data-testid="raster-banner">{rasterNote}</div> : null}
      {misaligned ? (
        <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-danger-bg)] px-4 py-1.5 text-[12.5px] text-[var(--color-danger)]" data-testid="misaligned-banner">
          <span>{t("boq.takeoff.misaligned", "The page on screen and the page data read by the server are in different positions, so measuring is locked to protect your quantities. Read the sheet again; if it persists, report this drawing.")}</span>
          {canEditPermission ? <Button size="sm" onClick={() => prepareOne.mutate(sheet.id)}>{t("boq.takeoff.retry", "Read again")}</Button> : null}
        </div>
      ) : null}

      <SheetStrip sheets={sheets} calibrations={overview.data?.calibrations ?? []} measurements={allMeasurements} currentId={sheet.id} onSelect={selectSheet} />
      <SheetIdentityBar sheet={sheet} drawingId={drawingId} canEdit={canEditPermission} />
      <SheetRolePanel sheets={sheets} drawingId={drawingId} canEdit={canEditPermission} currentSheetId={sheet.id} onSelect={selectSheet} />
      <ProjectPlansPanel drawingId={drawingId} canEdit={canEdit} drawings={(projectDrawings.data ?? []).filter((d) => d.is_current_revision).length} />
      <ProjectFactsPanel projectId={projectId} drawings={(projectDrawings.data ?? []).filter((d) => d.is_current_revision).length} />
      <AiShadowCard drawingId={drawingId} canEdit={canEditPermission} />
      <Toolbar
        tool={tool}
        onTool={(next) => { if (next === "ruler") setRulerPts([]); view.setTool(next); }}
        canDraw={canDraw}
        reason={drawBlock}
        canPick={canPick}
        snapOn={snapOn}
        snapAvailable={snapAvailable}
        snapKinds={snapKinds}
        onToggleSnap={view.toggleSnap}
        onToggleKind={view.toggleSnapKind}
        ortho={orthoLock}
        onOrtho={() => view.setOrtho(!orthoLock)}
        showMeasurements={showMeasurements}
        onToggleMeasurements={view.toggleMeasurements}
        onZoomIn={() => viewerRef.current?.zoomBy(1.3)}
        onZoomOut={() => viewerRef.current?.zoomBy(1 / 1.3)}
        onFit={() => viewerRef.current?.fit()}
      />

      <OverlayColourMenu mode={colourMode} onMode={setColourMode} />
      <ReadingGapsBar on={showReadingGaps} onToggle={setShowReadingGaps} data={readingGaps.data} loading={readingGaps.isFetching} error={readingGaps.error} />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <div className="relative min-h-[320px] flex-1">
          <PdfSheetViewer
            ref={viewerRef}
            page={page}
            snapIndex={snapIndex}
            snapActive={snapActive}
            snapKinds={snapKinds}
            cursor={cursor}
            panTool={tool === "pan"}
            paint={paint}
            paintKey={paintKey}
            onHover={onHover}
            onPick={onPick}
            onDoubleClick={onDoubleClick}
            onRenderState={setRenderState}
          />
          {pdf.status === "loading" || (!page && pdf.status === "ready") ? (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/10 text-[13px] font-semibold text-white" data-testid="pdf-loading">
              {t("boq.takeoff.loadingPdf", "Loading the drawing…")} {pdf.status === "loading" && pdf.progress ? `${Math.round(pdf.progress * 100)}%` : ""}
            </div>
          ) : null}
          {pdf.status === "error" || renderState === "error" ? (
            <div className="absolute inset-x-4 top-4 rounded-[8px] bg-[var(--color-danger-bg)] p-3 text-[13px] text-[var(--color-danger)]" data-testid="pdf-error">{t("boq.takeoff.pdfError", "The drawing could not be shown. Reload the page; if it persists, upload the PDF again.")}</div>
          ) : null}
          <div ref={statusRef} className="pointer-events-none absolute bottom-2 left-2 rounded-[6px] bg-black/55 px-2 py-0.5 font-mono text-[11px] text-white empty:hidden" data-testid="status" />
          {picking ? <div className="pointer-events-none absolute right-3 top-3 rounded-[6px] bg-black/60 px-2 py-1 text-[12px] text-white">{t("boq.takeoff.picking", "Looking…")}</div> : null}
        </div>

        <aside className="flex max-h-[50dvh] min-h-0 flex-col border-t border-[var(--color-border)] bg-[var(--color-surface)] lg:max-h-none lg:w-[400px] lg:border-l lg:border-t-0" data-testid="side-panel">
          <div className="flex shrink-0 border-b border-[var(--color-border)]" role="tablist">
            {TABS.map((x) => (
              <button
                key={x}
                type="button"
                role="tab"
                aria-selected={tab === x}
                data-testid={`tab-${x}`}
                onClick={() => view.setTab(x)}
                className={`flex-1 px-2 py-2.5 text-[12.5px] font-semibold ${tab === x ? "border-b-2 border-[var(--color-trace-gold)] text-[var(--color-text-primary)]" : "text-[var(--color-text-muted)]"}`}
              >
                {x === "measure" ? t("boq.takeoff.tab.measure", "Measure") : x === "list" ? `${t("boq.takeoff.tab.list", "List")} ${measurements.length || ""}` : x === "scale" ? t("boq.takeoff.tab.scale", "Scale") : x === "counts" ? t("boq.takeoff.tab.counts", "Counts") : x === "found" ? t("boq.takeoff.tab.found", "Found") : x === "frame" ? t("boq.takeoff.tab.frame", "Frame") : t("boq.takeoff.tab.results", "Results")}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {tab === "measure" ? (
              <MeasurePanel
                kind={kind}
                editingLabel={editing ? editing.label || editing.tag || editing.id.slice(0, 4) : null}
                form={form}
                onForm={setForm}
                modes={modes.data}
                preview={preview}
                geometryHint={geom.hint}
                formErrors={formErrors}
                pointCount={draft ? draft.points.length + draft.holes.reduce((n, h) => n + h.length, 0) : 0}
                originNote={originNote}
                blockedReason={reservedBlock ?? (editing ? readOnlyReason : drawBlock)}
                saving={saving}
                canEdit={canEdit}
                onSave={(c) => void save(c)}
                onCancel={cancelDraft}
                onAddHole={view.startHole}
                onFinishHole={view.finishHole}
                drawingHole={draft?.activeHole !== null && draft?.activeHole !== undefined}
                onToggleClosed={() => draft && view.setDraft({ ...draft, closed: !draft.closed })}
                closed={draft?.closed}
              />
            ) : null}
            {tab === "list" ? (
              <MeasurementList
                measurements={measurements}
                selectedIds={selectedIds}
                canEdit={canEdit}
                busy={busy}
                failures={failures}
                onSelect={view.select}
                onFocus={(id) => { view.focus(id); const m = measurements.find((x) => x.id === id); if (m) focusMeasurement(m); }}
                onConfirm={(id) => void confirmOne(id)}
                onUnconfirm={(id) => void unconfirmOne(id)}
                onDelete={(id) => { const m = measurements.find((x) => x.id === id); if (!m) return; if (m.status === "CONFIRMED") setDeleteMeasTarget(m); else { setDeleteMeasTarget(null); deleteMeas.mutate(id, { onSuccess: afterChange }); } }}
                onEdit={startEdit}
                onBulkConfirm={(ids) => void confirmMany(ids)}
              />
            ) : null}
            {tab === "scale" ? (
              <ScalePanel
                sheet={sheet}
                calibrations={calibrations}
                analysis={analysis.data}
                analysisLoading={analysis.isLoading}
                canEdit={canEdit}
                busy={autoCal.isPending || createCal.isPending || makeDefault.isPending || deleteCal.isPending}
                capture={capture}
                onCapture={startCapture}
                onClearCapture={() => { setCapture(NO_CAPTURE); if (tool === "calibrate") view.setTool("select"); }}
                onAuto={runAuto}
                onManual={runManual}
                onMakeDefault={(id) => makeDefault.mutate(id, { onSuccess: (c) => { calibrationToast(c); afterChange(); }, onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.scale.failed", "Could not set the scale"), description: takeoffErrorMessage(e) }) })}
                onDelete={(id) => setDeleteCalTarget(id)}
                showDims={showDimensions}
                onToggleDims={view.toggleDimensions}
                alignmentNote={misaligned ? t("boq.takeoff.misalignedShort", "The sheet on screen does not line up with the sheet data ({{m}} of {{c}} sampled words matched). Measuring is locked.", { m: alignment?.matched ?? 0, c: alignment?.checked ?? 0 }) : null}
              />
            ) : null}
            {tab === "counts" ? (
              <CountsPanel
                tags={tags.data?.tags}
                shapes={shapes.data}
                measurements={measurements}
                canEdit={canEdit}
                blocked={drawBlock}
                busy={saving}
                onPreviewTag={(tg) => void previewTag(tg)}
                onUseTag={(tg) => void applyTag(tg)}
                onPreviewShape={(id) => void applyShape(id, true)}
                onUseShape={(id) => void applyShape(id, false)}
                onClear={() => setSuggestionPts([])}
              />
            ) : null}
            {tab === "found" && sheet ? (
              <FoundTab
                key={sheet.id}
                sheet={sheet}
                drawingId={drawingId}
                canEdit={canEdit}
                scaleReady={Boolean(defaultCal)}
                onGoScale={() => view.setTab("scale")}
                onShow={showCandidate}
                onOpenMeasurement={openMeasurementById}
                showPlans={showPlans}
                onShowPlans={setShowPlans}
                onOpenSheet={selectSheet}
                onShowBox={(b) => { const padX = (b.x1 - b.x0) * 0.04, padY = (b.y1 - b.y0) * 0.04; viewerRef.current?.focusBox({ x0: b.x0 - padX, y0: b.y0 - padY, x1: b.x1 + padX, y1: b.y1 + padY }); }}
              />
            ) : null}
            {tab === "found" && sheet ? <CompanyConventionsPanel canManage={canManageCompany} /> : null}
            {tab === "frame" ? (
              <FramePanel
                frame={frame.data}
                loading={frame.isLoading}
                error={frame.isError}
                onRetry={() => void frame.refetch()}
                canEdit={canEdit}
                busy={placeFrame.isPending || frameRef.isPending}
                onPlace={(body) => placeFrame.mutate(body, { onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.frame.failed", "Could not save the placement"), description: takeoffErrorMessage(e) }) })}
                onReference={(v) => frameRef.mutate(v, { onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.frame.failed", "Could not save the placement"), description: takeoffErrorMessage(e) }) })}
              />
            ) : null}
            {tab === "frame" ? <FloorLevels datums={floors.data} loading={floors.isLoading} error={floors.isError} onRetry={() => void floors.refetch()} /> : null}
            {tab === "frame" ? (
              <ReconcilePanel data={reconcile.data} loading={reconcile.isLoading} error={reconcile.isError} onRetry={() => void reconcile.refetch()}
                model={reconcileModel} onModel={setReconcileModel} onShift={(dx, dy) => setReconcileShift([dx, dy])} />
            ) : null}
            {tab === "results" ? (
              <ResultsPanel
                data={recon.data}
                loading={recon.isLoading}
                error={recon.isError}
                onRetry={() => void recon.refetch()}
                canEdit={canEdit}
                onMode={(id, mode: ReconMode) => updateMeas.mutate({ id, body: { recon_mode: mode } }, { onSuccess: () => { afterChange(); showToast({ tone: "success", title: t("boq.takeoff.results.modeSaved", "Saved. Run the calculation again to apply it.") }); }, onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.saveFailed", "Could not save the measurement"), description: takeoffErrorMessage(e) }) })}
                onOpen={(sid, mid) => { if (sid && sid !== sheetId) setSearch((p) => { const n = new URLSearchParams(p); n.set("sheet", sid); n.set("m", mid); return n; }, { replace: true }); else { deepLinked.current = null; setSearch((p) => { const n = new URLSearchParams(p); n.set("m", mid); return n; }, { replace: true }); } }}
                onGoToRun={() => navigate(projectId ? `/app/projects/${projectId}` : "/app/projects")}
              />
            ) : null}
          </div>
        </aside>
      </div>

      {deleteMeasTarget ? (
        <ConfirmDialog
          title={t("boq.takeoff.deleteTitle", "Delete this confirmed measurement?")}
          description={t("boq.takeoff.deleteDesc", "It is counted in the BOQ. Deleting it removes it from the next calculation.")}
          confirmLabel={t("boq.takeoff.list.delete", "Delete")}
          pending={deleteMeas.isPending}
          onConfirm={() => void doDeleteMeasurement()}
          onClose={() => setDeleteMeasTarget(null)}
        />
      ) : null}
      {deleteCalTarget ? (
        <ConfirmDialog
          title={t("boq.takeoff.scale.removeTitle", "Remove this calibration?")}
          description={t("boq.takeoff.scale.removeDesc", "Measurements that use it must be moved to another calibration first.")}
          confirmLabel={t("boq.takeoff.scale.remove", "Remove")}
          pending={deleteCal.isPending}
          error={deleteCal.isError ? takeoffErrorMessage(deleteCal.error) : null}
          onConfirm={() => deleteCal.mutate(deleteCalTarget, { onSuccess: () => { setDeleteCalTarget(null); afterChange(); } })}
          onClose={() => { deleteCal.reset(); setDeleteCalTarget(null); }}
        />
      ) : null}
    </div>
  );
}
