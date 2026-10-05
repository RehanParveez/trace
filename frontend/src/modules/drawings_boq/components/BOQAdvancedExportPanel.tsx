import { useState } from "react";
import {Button, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import {useBOQSnapshots, useExportAdvancedBOQ,
} from "../hooks";
import type {ExportKind,
} from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

interface BOQAdvancedExportPanelProps {
  versionId: string;
  label: string;
  canExport: boolean;
}

const EXPORTS: Array<{
  kind: ExportKind;
  labelKey: string;
}> = [
  {
    kind: "CONTRACT_BOQ", labelKey: "boq.advancedExport.contractBoq",
  },
  {
    kind: "PROCUREMENT", labelKey: "boq.advancedExport.procurement",
  },
  {
    kind: "MEASUREMENT_BOOK", labelKey: "boq.advancedExport.measurementBook",
  },
  {
    kind: "AUDIT_REPORT", labelKey: "boq.advancedExport.auditReport",
  },
  {
    kind: "REVISION_COMPARISON", labelKey: "boq.advancedExport.revisionComparison",
  },
  {
    kind: "BBS", labelKey: "boq.advancedExport.bbs",
  },
];

export function BOQAdvancedExportPanel({
  versionId,
  label,
  canExport,
}: BOQAdvancedExportPanelProps) {
  const { t } = useTranslation();

  const [kind, setKind] =
    useState<ExportKind>(
      "CONTRACT_BOQ",
    );

  const [format, setFormat] =
    useState<"pdf" | "xlsx">(
      "pdf",
    );

  const [snapshotId, setSnapshotId] =
    useState<string | null>(
      null,
    );

  const snapshots = useBOQSnapshots(versionId);

  const exportMutation =
    useExportAdvancedBOQ(
      versionId,
      label,
    );

  const { showToast } = useToast();

  function exportFile() {
    exportMutation.mutate(
      {
        kind,
        format,
        snapshotId,
      },
      {
        onSuccess: () =>
          showToast({
            tone: "success",
            title:
              t("boq.advancedExport.exportGenerated"),
          }),
      },
    );
  }

  if (!canExport) {
    return null;
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.advancedExport.eyebrow")}
        title={t("boq.advancedExport.title")}
        description={t("boq.advancedExport.description")}
      />

      <div className="grid gap-3 p-5 md:grid-cols-3">
        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {t("boq.advancedExport.export")}
          </span>

          <select
            value={kind}
            onChange={(event) =>
              setKind(
                event.target
                  .value as ExportKind,
              )
            }
            className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
          >
            {EXPORTS.map(
              (option) => (
                <option
                  key={option.kind}
                  value={
                    option.kind
                  }
                >
                  {t(option.labelKey)}
                </option>
              ),
            )}
          </select>
        </label>

        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {t("boq.advancedExport.format")}
          </span>

          <select
            value={format}
            onChange={(event) =>
              setFormat(
                event.target
                  .value as
                  | "pdf"
                  | "xlsx",
              )
            }
            className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
          >
            <option value="pdf">
              {t("boq.advancedExport.pdf")}
            </option>
            <option value="xlsx">
              {t("boq.advancedExport.xlsx")}
            </option>
          </select>
        </label>

        <label className="block">
          <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {t("boq.advancedExport.snapshot")}
          </span>

          <select
            value={snapshotId ?? ""}
            onChange={(event) =>
              setSnapshotId(
                event.target.value ||
                  null,
              )
            }
            className="mt-1.5 w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12px]"
          >
            <option value="">
              {t("boq.advancedExport.currentVersion")}
            </option>

            {(snapshots.data ?? []).map(
              (snapshot) => (
                <option
                  key={snapshot.id}
                  value={
                    snapshot.id
                  }
                >
                  {t("boq.advancedExport.snapshotVersion", {
                    version: snapshot.version_no,
                    purpose: snapshot.purpose,
                  })}
                </option>
              ),
            )}
          </select>
        </label>
      </div>

      <div className="flex justify-end border-t border-[var(--color-border)] p-5">
        <Button
          variant="primary"
          disabled={
            exportMutation.isPending
          }
          onClick={exportFile}
        >
          {exportMutation.isPending
            ? t("boq.advancedExport.generating")
            : t("boq.advancedExport.generateExport")}
        </Button>
      </div>
    </Panel>
  );
}