import { useEffect, useRef, useState } from "react";
import { Badge, Button, useToast } from "../../../organizations/components/OrganizationUi";
import { useDownloadExportJob, useExportJob } from "../hooks/useRecalculation";
import type { ExportJob } from "../types/recalculation.types";
import {blobErrorMessage, downloadErrorKind, exportJobFilename, exportJobStatusLabel, exportJobTone, formatBytes, isExportJobActive, jobAgeMinutes,
} from "../utils/recalculation.utils";
import { useScaleT } from "../utils/useRecalculationT";

interface ExportJobCardProps {
  job: ExportJob;
  kindLabel: string;
  onRequestAgain?: () => void;
  onDismiss?: () => void;
}

export function ExportJobCard({ job: initial, kindLabel, onRequestAgain, onDismiss }: ExportJobCardProps) {
  const t = useScaleT();
  const { showToast } = useToast();
  const query = useExportJob(initial);
  const job = query.data ?? initial;
  const download = useDownloadExportJob();
  const [expired, setExpired] = useState(false);
  const announced = useRef(false);

  useEffect(() => {
    if (announced.current || initial.status === "SUCCEEDED") return;
    if (job.status === "SUCCEEDED") {
      announced.current = true;
      showToast({ tone: "success", title: t("scale.export.readyToast", "Your export is ready"), description: kindLabel });
    }
  }, [job.status, initial.status, kindLabel, showToast, t]);

  function startDownload() {
    download.mutate(job, {
      onSuccess: () => showToast({ tone: "success", title: t("scale.export.downloaded", "Export downloaded") }),
      onError: async (error) => {
        if (downloadErrorKind(error) === "expired") {
          setExpired(true);
          return;
        }
        showToast({
          tone: "error",
          title: t("scale.export.downloadFailed", "Couldn't download the export"),
          description: await blobErrorMessage(error, t("scale.export.downloadFailedDesc", "Try again in a moment.")),
        });
      },
    });
  }

  const active = isExportJobActive(job.status);
  const waitingLong = active && jobAgeMinutes(job) >= 5;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[8px] border border-[var(--color-border)] p-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">{kindLabel}</span>
          <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{job.format}</span>
          <Badge tone={exportJobTone(job.status)}>{exportJobStatusLabel(t, job.status)}</Badge>
        </div>
        <div className="mt-1 text-[11px] text-[var(--color-text-muted)]">
          {job.status === "SUCCEEDED" && !expired
            ? t("scale.export.readyNote", "{{name}} · {{size}}", { name: exportJobFilename(job), size: formatBytes(job.file_size_bytes) })
            : null}
          {active
            ? waitingLong
              ? t("scale.export.slowNote", "Still waiting after {{min}} minutes. The queue may be busy; you can leave this page and request it again later.", { min: jobAgeMinutes(job) })
              : t("scale.export.activeNote", "This is a large export, so it is being prepared in the background. You can keep working.")
            : null}
          {job.status === "FAILED"
            ? job.error_message || t("scale.export.failedNote", "The export could not be generated.")
            : null}
          {expired ? t("scale.export.expired", "The stored file has expired. Request it again.") : null}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {job.status === "SUCCEEDED" && !expired ? (
          <Button size="sm" variant="primary" disabled={download.isPending} onClick={startDownload}>
            {download.isPending ? t("scale.export.downloading", "Downloading…") : t("scale.export.download", "Download")}
          </Button>
        ) : null}
        {(job.status === "FAILED" || expired) && onRequestAgain ? (
          <Button size="sm" variant="secondary" onClick={onRequestAgain}>
            {t("scale.export.requestAgain", "Request again")}
          </Button>
        ) : null}
        {!active && onDismiss ? (
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            {t("scale.start.dismiss", "Dismiss")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
