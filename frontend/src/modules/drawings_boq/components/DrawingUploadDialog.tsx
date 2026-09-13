import { useRef, useState } from "react";
import { Button, Icon, Modal } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { QuotaLimitNotice, useQuotaStatus } from "../../subscriptions";
import { useUploadDrawing } from "../hooks";
import { formatFileSize } from "../utils/drawings-boq.utils";
import { useTranslation } from "react-i18next";

interface DrawingUploadDialogProps {
  projectId: string;
  onClose: () => void;
}

export function DrawingUploadDialog({ projectId, onClose }: DrawingUploadDialogProps) {
  const { t } = useTranslation();
  const upload = useUploadDrawing(projectId);
  const drawingQuota = useQuotaStatus("drawings");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const idempotencyKeyRef = useRef(crypto.randomUUID());
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setError(null);

    if (selected && !selected.name.toLowerCase().endsWith(".ifc")) {
      setError(t("drawings.upload.ifcOnly"))
      setFile(null);
      return;
    }

    setFile(selected);
  }

  function submit() {
    if (!file) return;

    upload.mutate(
      { file, idempotencyKey: idempotencyKeyRef.current },
      {
        onSuccess: onClose,
        onError: (error) =>
          setError(getApiErrorMessage(error, t("drawings.upload.failed")))
      },
    );
  }

  return (
    <Modal title={t("drawings.upload.title")} description={t("drawings.upload.description")} onClose={onClose}>
      <div className="space-y-4">
        {drawingQuota.isAtLimit ? (
          <QuotaLimitNotice
            message={t("drawings.upload.quotaLimit", { count: drawingQuota.limit, limit: drawingQuota.limit })}
          />
        ) : null}

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center transition hover:border-[var(--color-trace-gold-dark)]"
        >
          <Icon name="download" size={20} className="text-[var(--color-text-muted)]" />
          <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{file ? file.name : t("drawings.upload.chooseFile")}</span>
          <span className="text-[12px] text-[var(--color-text-muted)]">{file ? formatFileSize(file.size) : t("drawings.upload.ifcOnlyHint")}</span>
        </button>

        <input ref={inputRef} type="file" accept=".ifc" onChange={handleFileChange} className="hidden" />

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={upload.isPending}>{t("common.cancel")}</Button>
          <Button variant="primary" onClick={submit} disabled={!file || upload.isPending || drawingQuota.isAtLimit}>
            {upload.isPending ? t("drawings.upload.uploading") : t("drawings.upload.submit")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}