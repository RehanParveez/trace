import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "../../../organizations/components/OrganizationUi";
import { useWorkItems } from "../../standards/hooks";
import { useAcceptCandidates, useDecideCandidates, useExtractSheet, useSheetCandidates } from "../hooks/useTakeoff";
import type { TakeoffCandidate, TakeoffSheet } from "../types/takeoff.types";
import { buildAcceptBody, NO_HEIGHTS } from "../utils/candidates";
import type { Heights } from "../utils/candidates";
import { takeoffErrorMessage } from "../utils/errors";
import type { SteelSet } from "../utils/steel";
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

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [heights, setHeights] = useState<Heights>(NO_HEIGHTS);
  const [items, setItems] = useState<Record<string, string>>({});
  const [steel, setSteel] = useState<Record<string, SteelSet>>({});

  const codes = useMemo(() => (workItems.data ?? []).filter((w) => w.is_active).map((w) => w.code).sort(), [workItems.data]);

  const forget = (ids: string[]) => {
    setSelected((s) => { const n = new Set(s); ids.forEach((id) => n.delete(id)); return n; });
    setSteel((s) => { const n = { ...s }; ids.forEach((id) => delete n[id]); return n; });
  };

  function onAccept(ids: string[]) {
    if (ids.length === 0) return;
    accept.mutate(buildAcceptBody(ids, heights, items, steel), {
      onSuccess: (r) => {
        forget(r.accepted.map((a) => a.id));
        if (r.accepted.length) showToast({ tone: "success", title: t("boq.takeoff.found.accepted", "{{n}} added to your measurements", { n: r.accepted.length }) });
        if (r.failed.length) showToast({ tone: "error", title: t("boq.takeoff.found.acceptFailed", "{{n}} could not be added", { n: r.failed.length }), description: r.failed[0]?.message });
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

  return (
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
      onHeights={setHeights}
      workItems={items}
      onWorkItems={setItems}
      workItemCodes={codes}
      onRead={(auto) => extract.mutate({ sheetId: sheet.id, autoCalibrate: auto })}
      onGoScale={p.onGoScale}
      onShow={p.onShow}
      steel={steel}
      onSteel={(id, s) => setSteel((cur) => { const n = { ...cur }; if (s) n[id] = s; else delete n[id]; return n; })}
      onAccept={onAccept}
      onReject={(ids) => onDecide("reject", ids)}
      onRestore={(ids) => onDecide("restore", ids)}
      onOpenMeasurement={p.onOpenMeasurement}
    />
  );
}
