import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "../../../organizations/components/OrganizationUi";
import { useWorkItems } from "../../standards/hooks";
import { useAcceptCandidates, useChooseFloorSources, useCheckKnownFacts, useDecideCandidates, useExtractSheet, useReadyToAccept, useReaderTrace, useSheetCandidates, useTakeoffCrossChecks, useTakeoffFloorSources, useTakeoffTypedMemory } from "../hooks/useTakeoff";
import type { CandidateFailure, FloorChoiceBody, TakeoffCandidate, TakeoffSheet } from "../types/takeoff.types";
import { buildAcceptBody, kindKey, NO_HEIGHTS } from "../utils/candidates";
import type { Heights } from "../utils/candidates";
import { takeoffErrorMessage } from "../utils/errors";
import { autoChoiceLine, choiceToast, hasPlans, planBoxOf } from "../utils/floorSources";
import type { SteelSet } from "../utils/steel";
import { CrossChecksPanel } from "./CrossChecksPanel";
import { KnownFactsPanel } from "./KnownFactsPanel";
import { ReaderTracePanel } from "./ReaderTracePanel";
import { DetailOnlyPanel } from "../detail_only/components/DetailOnlyPanel";
import { PrintedGradesPanel } from "../grades/components/PrintedGradesPanel";
import { PrintedNotesPanel } from "../notes/components/PrintedNotesPanel";
import { IntegrityPanel } from "../integrity/components/IntegrityPanel";
import { DecisionsPanel } from "../decisions/components/DecisionsPanel";
import { ReadingAccuracyPanel } from "../reading_score/components/ReadingAccuracyPanel";
import { ReadyToAcceptPanel } from "./ReadyToAcceptPanel";
import { RepeatMarksNotice } from "./RepeatMarksNotice";
import { otherFailures, repeatMarks } from "../utils/repeatMarks";
import { FloorSourcesPanel } from "./FloorSourcesPanel";
import { FoundPanel } from "./FoundPanel";

interface Props {
  sheet: TakeoffSheet;
  drawingId: string | undefined;
  canEdit: boolean;
  scaleReady: boolean;
  focusId?: string | null;
  onGoScale: () => void;
  onShow: (c: TakeoffCandidate) => void;
  onOpenMeasurement: (measurementId: string) => void;
  showPlans: boolean;
  onShowPlans: (on: boolean) => void;
  onOpenSheet: (sheetId: string) => void;
  onShowBox: (box: { x0: number; y0: number; x1: number; y1: number }) => void;
}

export function FoundTab(p: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const sheet = p.sheet;
  const list = useSheetCandidates(sheet);
  const extract = useExtractSheet(p.drawingId);
  const accept = useAcceptCandidates(p.drawingId, sheet.id);
  const decide = useDecideCandidates(p.drawingId, sheet.id);
  const workItems = useWorkItems();
  const floorSources = useTakeoffFloorSources(p.drawingId);
  const crossChecks = useTakeoffCrossChecks(p.drawingId);
  const typedMemory = useTakeoffTypedMemory(p.drawingId);
  const knownFacts = useCheckKnownFacts(p.drawingId);
  const readerTrace = useReaderTrace(p.drawingId);
  const ready = useReadyToAccept(p.drawingId);
  const choose = useChooseFloorSources(p.drawingId);
  const stats = list.data?.extraction.stats;
  const planFloors = useMemo(() => ["FOUNDATION", "BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH", "TYPICAL", "ROOF"].filter((f) => planBoxOf(stats, f) !== null), [stats]);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [heights, setHeights] = useState<Heights>(NO_HEIGHTS);
  const [items, setItems] = useState<Record<string, string>>({});
  const [steel, setSteel] = useState<Record<string, SteelSet>>({});
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [repeat, setRepeat] = useState<CandidateFailure[]>([]);

  const kinds = useMemo(() => Object.fromEntries((list.data?.candidates ?? []).map((c) => [c.id, kindKey(c)])), [list.data]);
  const codes = useMemo(() => (workItems.data ?? []).filter((w) => w.is_active).map((w) => w.code).sort(), [workItems.data]);

  const forget = (ids: string[]) => {
    setSelected((s) => { const n = new Set(s); ids.forEach((id) => n.delete(id)); return n; });
    setSteel((s) => { const n = { ...s }; ids.forEach((id) => delete n[id]); return n; });
    setPicks((s) => { const n = { ...s }; ids.forEach((id) => delete n[id]); return n; });
  };

  function onAccept(ids: string[], allowRepeat = false) {
    if (ids.length === 0) return;
     accept.mutate({ ...buildAcceptBody(ids, heights, items, steel, picks, kinds), ...(allowRepeat ? { allow_repeat_marks: true } : {}) }, {
      onSuccess: (r) => {
        forget(r.accepted.map((a) => a.id));
        setRepeat(repeatMarks(r.failed));
        if (r.accepted.length) showToast({ tone: "success", title: t("boq.takeoff.found.accepted", "{{n}} added to your measurements", { n: r.accepted.length }) });
        if (otherFailures(r.failed).length) showToast({ tone: "error", title: t("boq.takeoff.found.acceptFailed", "{{n}} could not be added", { n: otherFailures(r.failed).length }), description: otherFailures(r.failed)[0]?.message });
      },
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.found.acceptError", "Could not add the items"), description: takeoffErrorMessage(e) }),
    });
  }

  function onDecide(action: "reject" | "restore", ids: string[]) {
    if (ids.length === 0) return;
    decide.mutate({ ids, action }, {
      onSuccess: (r) => { forget(r.changed); if (r.failed.length) showToast({ tone: "error", title: r.failed[0]?.message ?? t("boq.takeoff.found.decideFailed", "Some items could not be changed") }); },
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.found.decideError", "Could not change the items"), description: takeoffErrorMessage(e) }),
    });
  }

  function onChoose(body: FloorChoiceBody) {
    choose.mutate(body, {
      onSuccess: (r) => {
        setSelected(new Set());
        const msg = choiceToast(r);
        if (msg.ok) showToast({ tone: "success", title: t("boq.takeoff.floorSources.chosen", "Floors updated"), description: msg.ok });
        if (msg.problem) showToast({ tone: "error", title: t("boq.takeoff.floorSources.blocked", "Some floors could not be changed"), description: msg.problem });
      },
      onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.floorSources.failed", "Could not choose the sheet"), description: takeoffErrorMessage(e) }),
    });
  }

   return (
    <>
    {p.drawingId ? <IntegrityPanel drawingId={p.drawingId} version={list.dataUpdatedAt} /> : null}
    {p.drawingId ? <DecisionsPanel drawingId={p.drawingId} canEdit={p.canEdit} version={list.dataUpdatedAt} /> : null}
    <FloorSourcesPanel
      data={floorSources.data}
      loading={floorSources.isLoading}
      error={floorSources.isError}
      onRetry={() => void floorSources.refetch()}
      canEdit={p.canEdit}
      busy={choose.isPending}
      currentSheetId={sheet.id}
      planFloors={planFloors}
      sheetHasPlans={hasPlans(stats)}
      showPlans={p.showPlans}
      onShowPlans={p.onShowPlans}
      onChoose={onChoose}
      onOpenSheet={p.onOpenSheet}
      onShowPlan={(floor) => { const b = planBoxOf(stats, floor); if (b) p.onShowBox(b); }}
    />
    <KnownFactsPanel result={knownFacts.data} busy={knownFacts.isPending} failed={knownFacts.isError} onCheck={(facts) => knownFacts.mutate(facts)} />
    <ReaderTracePanel data={readerTrace.data} loading={readerTrace.isLoading} error={readerTrace.isError} onRetry={() => void readerTrace.refetch()} />
    {p.drawingId ? <DetailOnlyPanel drawingId={p.drawingId} canEdit={p.canEdit} /> : null}
    {p.drawingId ? <PrintedGradesPanel drawingId={p.drawingId} canEdit={p.canEdit} /> : null}
    {p.drawingId ? <PrintedNotesPanel drawingId={p.drawingId} version={list.dataUpdatedAt} /> : null}
    {p.drawingId ? <ReadingAccuracyPanel drawingId={p.drawingId} canEdit={p.canEdit} /> : null}
    <RepeatMarksNotice
      failures={repeat}
      canEdit={p.canEdit}
      busy={accept.isPending || decide.isPending}
      onAcceptAnyway={(ids) => { setRepeat([]); onAccept(ids, true); }}
      onReject={(ids) => { setRepeat([]); onDecide("reject", ids); }}
      onDismiss={() => setRepeat([])}
    />
    <ReadyToAcceptPanel data={ready.data} pageNo={sheet.page_no} canEdit={p.canEdit} busy={accept.isPending || decide.isPending} onAccept={onAccept} />
    <FoundPanel
      sheet={sheet}
      data={list.data}
      loading={list.isLoading}
      loadError={list.isError ? takeoffErrorMessage(list.error) : null}
      onRetryLoad={() => void list.refetch()}
      canEdit={p.canEdit}
      scaleReady={p.scaleReady}
      scaleRecommended={Boolean(sheet.detected_scale?.recommended)}
      reading={extract.isPending}
      readError={extract.isError ? takeoffErrorMessage(extract.error) : null}
      busy={accept.isPending || decide.isPending}
      blocked={null}
      selected={selected}
      onSelected={setSelected}
      focusId={p.focusId ?? null}
      heights={heights}
      memory={typedMemory.data?.values}
      onHeights={setHeights}
      workItems={items}
      onWorkItems={setItems}
      workItemCodes={codes}
      onRead={(auto) => extract.mutate({ sheetId: sheet.id, autoCalibrate: auto }, {
        onSuccess: (r) => {
          const line = autoChoiceLine(r.floors_chosen);
          if (line) showToast({ tone: "info", title: t("boq.takeoff.floorSources.autoChosen", "Floors drawn on two sheets are counted once"), description: line });
        },
      })}
      onGoScale={p.onGoScale}
      onShow={p.onShow}
      steel={steel}
      onSteel={(id, s) => setSteel((cur) => { const n = { ...cur }; if (s) n[id] = s; else delete n[id]; return n; })}
      picks={picks}
      onPick={(id, mark) => setPicks((cur) => { const n = { ...cur }; if (mark) n[id] = mark; else delete n[id]; return n; })}
      onAccept={onAccept}
      onReject={(ids) => onDecide("reject", ids)}
      onRestore={(ids) => onDecide("restore", ids)}
      onOpenMeasurement={p.onOpenMeasurement}
    />
    </>
  );
}
