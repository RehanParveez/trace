import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../../../identity";
import { Badge, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, useToast } from "../../../../organizations/components/OrganizationUi";
import { takeoffErrorMessage } from "../../utils/errors";
import { AccuracyReportView } from "../components/AccuracyReportView";
import { FlowBoq } from "../components/FlowBoq";
import { FlowSteps } from "../components/FlowSteps";
import { FlowTiming } from "../components/FlowTiming";
import { useExport, useFlowAccuracy, useFlowBoq, useFlowSeen, useFlowStatus, useRateBooks, useStartQuantities, useStartRead, useUploadDrawing } from "../hooks/useFlow";
import { EXPORT_TEXT, EXPORTS, saveBlob } from "../utils/flow";

export function FlowPage() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { projectId } = useParams<{ projectId: string }>();
  const [search, setSearch] = useSearchParams();
  const profile = search.get("profile");
  const bookId = search.get("book");
  const [showBoq, setShowBoq] = useState(false);
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ);
  const canEdit = permissions.includes(IDENTITY_PERMISSIONS.BOQ_UPDATE);
  const status = useFlowStatus(projectId, profile);
  const books = useRateBooks();
  const ready = status.data?.steps.find((s) => s.key === "boq")?.state === "READY";
  const boq = useFlowBoq(projectId, profile, bookId, showBoq && ready);
  const accuracy = useFlowAccuracy(projectId, profile, bookId, showBoq && ready);
  const seen = useFlowSeen(projectId);
  const upload = useUploadDrawing(projectId);
  const read = useStartRead(projectId);
  const quantities = useStartQuantities(projectId);
  const exporter = useExport(projectId, profile, bookId);
  const busy = upload.isPending || read.isPending || quantities.isPending || !canEdit;

  if (!canRead) return <EmptyState icon="alert" title={t("boq.flow.noAccess", "No access")} description={t("boq.flow.noAccessText", "You cannot read the drawings of this project.")} />;
  if (status.isLoading) return <LoadingState label={t("boq.flow.loading", "Loading the project…")} />;
  if (status.isError || !status.data) return <ErrorState title={t("boq.flow.loadError", "The project could not be loaded")} onRetry={() => void status.refetch()} />;

  const failed = (title: string) => (e: unknown) => showToast({ tone: "error", title, description: takeoffErrorMessage(e) });
  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(search);
    if (value) next.set(key, value); else next.delete(key);
    setSearch(next, { replace: true });
  };
  const openBoq = () => {
    setShowBoq(true);
    seen.mutate("boq");
  };
  const download = (kind: (typeof EXPORTS)[number]) => exporter.mutate(kind, {
    onSuccess: ({ blob, name }) => saveBlob(blob, name),
    onError: failed(t("boq.flow.exportFailed", "The export was not made")),
  });

  return (
    <div className="space-y-4 p-4" data-testid="flow-page">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-[Archivo] text-[20px] font-bold">{t("boq.flow.title", "Upload to priced BOQ")}</h1>
        {status.data.open_rows > 0 ? <Badge tone="gold">{t("boq.flow.openRows", "{{n}} review row(s) open", { n: status.data.open_rows })}</Badge> : null}
      </div>
      <Panel>
        <PanelHeader eyebrow={t("boq.flow.eyebrow", "Project")} title={t("boq.flow.steps", "Steps")} description={t("boq.flow.stepsText", "Every project goes through the same steps, including the review list, whatever the set.")} />
        <div className="p-4">
          <FlowSteps projectId={projectId as string} steps={status.data.steps} next={status.data.next} busy={busy} onOpenBoq={openBoq} onOpenReview={() => seen.mutate("review")}
            onUpload={(file) => upload.mutate(file, { onSuccess: () => showToast({ tone: "success", title: t("boq.flow.uploaded", "Drawing uploaded") }), onError: failed(t("boq.flow.uploadFailed", "The drawing was not uploaded")) })}
            onRead={() => read.mutate(undefined, { onSuccess: () => showToast({ tone: "success", title: t("boq.flow.readQueued", "The reading was started") }), onError: failed(t("boq.flow.readFailed", "The reading was not started")) })}
            onQuantities={() => quantities.mutate(undefined, { onSuccess: () => showToast({ tone: "success", title: t("boq.flow.calcQueued", "The calculation was started") }), onError: failed(t("boq.flow.calcFailed", "The calculation was not started")) })} />
        </div>
      </Panel>
      {showBoq && ready ? (
        <Panel>
          <PanelHeader eyebrow={t("boq.flow.eyebrow", "Project")} title={t("boq.flow.boq", "Priced BOQ")} description={t("boq.flow.boqText", "Every line shows its state, the money that is measured and the money that is assumed, and its range.")} />
          <div className="p-4">
            {boq.isLoading ? <LoadingState label={t("boq.flow.loadingBoq", "Pricing the lines…")} /> : boq.isError || !boq.data ? <ErrorState title={t("boq.flow.boqError", "The BOQ could not be priced")} onRetry={() => void boq.refetch()} /> : (
              <FlowBoq data={boq.data} profiles={status.data.profiles} profile={profile} profileSource={boq.data.profile_source} books={books.data ?? []} bookId={bookId}
                onProfile={(id) => setParam("profile", id)} onBook={(id) => setParam("book", id)} />
            )}
          </div>
        </Panel>
      ) : null}
      {showBoq && ready ? (
        <Panel>
          <PanelHeader eyebrow={t("boq.flow.eyebrow", "Project")} title={t("boq.flow.accuracy", "How much of this bill to trust")} description={t("boq.flow.accuracyText", "What was measured, what was assumed, what was not read, and what to check first.")} />
          <div className="p-4">
            {accuracy.isLoading ? <LoadingState label={t("boq.flow.loadingAccuracy", "Preparing the accuracy report…")} /> : accuracy.isError || !accuracy.data ? <ErrorState title={t("boq.flow.accuracyError", "The accuracy report could not be made")} onRetry={() => void accuracy.refetch()} /> : <AccuracyReportView report={accuracy.data} />}
          </div>
        </Panel>
      ) : null}
      <Panel>
        <PanelHeader eyebrow={t("boq.flow.eyebrow", "Project")} title={t("boq.flow.export", "Export")} description={t("boq.flow.exportText", "The workbook, the priced BOQ and the client report are made from the BOQ above, under the same profile and rate book.")} />
        <div className="flex flex-wrap gap-2 p-4">
          {EXPORTS.map((kind) => (
            <button key={kind} type="button" className="rounded-full border border-[var(--color-border)] px-3 py-1 text-[12.5px] font-semibold disabled:opacity-50" disabled={!ready || exporter.isPending} onClick={() => download(kind)} data-testid={`flow-export-${kind}`}>
              {EXPORT_TEXT[kind]}
            </button>
          ))}
        </div>
      </Panel>
      <Panel>
        <PanelHeader eyebrow={t("boq.flow.eyebrow", "Project")} title={t("boq.flow.timing", "Time")} description={t("boq.flow.timingText", "The seconds of each step, recorded as the project goes through.")} />
        <div className="p-4"><FlowTiming sitting={status.data.sitting} /></div>
      </Panel>
    </div>
  );
}
