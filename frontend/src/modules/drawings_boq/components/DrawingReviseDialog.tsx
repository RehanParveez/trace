import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {Button, Field, Icon, inputClass, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useReviseDrawing } from "../hooks";
import type { Drawing } from "../types/drawings-boq.types";

interface DrawingReviseDialogProps {
  projectId: string;
  previousDrawing: Drawing;
  onClose: () => void;
}

export function DrawingReviseDialog({
  projectId,
  previousDrawing,
  onClose,
}: DrawingReviseDialogProps) {
  const { t } = useTranslation();
  const revise = useReviseDrawing(projectId);
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [revisionLabel, setRevisionLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const selected =
      event.target.files?.[0] ?? null;

    const lowerName = selected?.name.toLowerCase() ?? "";

    if (
      selected &&
      !lowerName.endsWith(".ifc") &&
      !lowerName.endsWith(".pdf")
    ) {
      setError(
        t("drawings.revise.invalidFileType"),
      );
      setFile(null);
      return;
    }

    setError(null);
    setFile(selected);
  }

  function submit() {
    if (!file) {
      return;
    }

    revise.mutate(
      {
        drawingId: previousDrawing.id,
        file,
        revisionLabel:
          revisionLabel.trim() || null,
      },
      {
        onSuccess: () => {
          onClose();

          showToast({
            tone: "success",
            title: t(
              "drawings.revise.successTitle",
            ),
          });
        },

        onError: (errorResponse) => {
          setError(
            getApiErrorMessage(
              errorResponse,
              t(
                "drawings.revise.errorFallback",
              ),
            ),
          );
        },
      },
    );
  }

  return (
    <Modal
      title={t("drawings.revise.title")}
      description={t(
        "drawings.revise.description",
        {
          filename:
            previousDrawing.original_filename,
        },
      )}
      onClose={onClose}
    >
      <div className="space-y-4">
        <button
          type="button"
          onClick={() =>
            inputRef.current?.click()
          }
          className="flex w-full flex-col items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center transition hover:border-[var(--color-trace-gold-dark)]"
        >
          <Icon
            name="download"
            size={20}
            className="text-[var(--color-text-muted)]"
          />

          <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">
            {file
              ? file.name
              : t(
                  "drawings.revise.chooseFile",
                )}
          </span>
        </button>

        <input
          ref={inputRef}
          type="file"
          accept=".ifc,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />

        <Field
          label={t(
            "drawings.revise.revisionLabel",
          )}
          hint={t(
            "drawings.revise.revisionLabelHint",
          )}
        >
          <input
            className={inputClass}
            value={revisionLabel}
            onChange={(event) =>
              setRevisionLabel(
                event.target.value,
              )
            }
            placeholder={t(
              "drawings.revise.revisionLabelPlaceholder",
            )}
          />
        </Field>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={revise.isPending}
          >
            {t("common.cancel")}
          </Button>

          <Button
            variant="primary"
            onClick={submit}
            disabled={!file || revise.isPending}
          >
            {revise.isPending
              ? t(
                  "drawings.revise.uploading",
                )
              : t(
                  "drawings.revise.uploadButton",
                )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}