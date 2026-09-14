import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, TableShell, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import type { Drawing } from "../types/drawings-boq.types";
import { formatDrawingStatus, formatFileSize, getDrawingStatusTone, isDrawingInProgress } from "../utils/drawings-boq.utils";
import { useSuggestItemsFromPdf, useViewDrawingFile } from "../hooks";
import { useTranslation } from "react-i18next";

interface DrawingTableProps {
  projectId: string;
  drawings: Drawing[];
  canUpload: boolean;
  canSuggestItems: boolean;
  quotaBlocked?: boolean;
  onUpload: () => void;
  onView: (drawing: Drawing) => void;
  onItemsSuggested?: (boqVersionId: string) => void;
}

export function DrawingTable({
  projectId,
  drawings,
  canUpload,
  canSuggestItems,
  quotaBlocked = false,
  onUpload,
  onView,
  onItemsSuggested,
}: DrawingTableProps) {
  const { t } = useTranslation();
  const viewFile = useViewDrawingFile();
  const suggestItems = useSuggestItemsFromPdf(projectId);
  const { showToast } = useToast();

  function handleSuggestItems(drawing: Drawing) {
    suggestItems.mutate(drawing.id, {
      onSuccess: (result) => {
        if (result.created_item_count === 0) {
          showToast({
            tone: "info",
            title: t("drawings.suggest.noDataTitle"),
            description: t("drawings.suggest.noDataDesc", {
              filename: drawing.original_filename,
            }),
          });
          return;
        }

        showToast({
          tone: "success",
          title: t("drawings.suggest.successTitle", {
            count: result.created_item_count,
          }),
          description: t("drawings.suggest.successDesc"),
        });

        onItemsSuggested?.(result.boq_version_id);
      },
      onError: (error) =>
        showToast({
          tone: "error",
          title: t("drawings.suggest.errorTitle"),
          description: getApiErrorMessage(error, t("drawings.suggest.errorFallback")),
        }),
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("drawings.table.eyebrow")}
        title={t("drawings.table.title")}
        description={t("drawings.table.description")}
        action={
          canUpload ? (
            <Button
              variant="primary"
              size="sm"
              onClick={onUpload}
              disabled={quotaBlocked}
              title={quotaBlocked ? t("drawings.table.quotaTitle") : undefined}
            >
              <Icon name="plus" size={13} />
              {t("drawings.table.upload")}
            </Button>
          ) : null
        }
      />


      {drawings.length === 0 ? (
        <EmptyState
          icon="building"
          title={t("drawings.table.emptyTitle")}
          description={t("drawings.table.emptyDesc")}
          action={
            canUpload ? (
              <Button
                variant="primary"
                size="sm"
                onClick={onUpload}
                disabled={quotaBlocked}
                title={quotaBlocked ? t("drawings.table.quotaTitle") : undefined}
              >
                {t("drawings.table.upload")}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <TableShell>
          <table className="w-full min-w-[640px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">{t("drawings.table.colFile")}</th>
                <th className="px-4 py-3">{t("drawings.table.colFormat")}</th>
                <th className="px-4 py-3">{t("drawings.table.colStatus")}</th>
                <th className="px-4 py-3">{t("drawings.table.colSize")}</th>
                <th className="px-4 py-3 text-right">{t("drawings.table.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {drawings.map((drawing) => {
                const isReference = drawing.format === "PDF";

                return (
                  <tr key={drawing.id} className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
                    <td className="px-4 py-3.5">
                      <button
                        type="button"
                        onClick={() => {
                          if (isReference) {
                            viewFile.mutate(drawing.id);
                            return;
                          }
                          onView(drawing);
                        }}
                        className="text-left"
                      >
                        <span className="block truncate text-[14px] font-semibold text-[var(--color-text-primary)]">{drawing.original_filename}</span>
                        {drawing.error_message ? (
                          <span className="mt-0.5 block max-w-[320px] truncate text-[12px] text-[var(--color-danger)]">{drawing.error_message}</span>
                        ) : null}
                      </button>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[12px] text-[var(--color-text-secondary)]">{drawing.format}</td>
                    <td className="px-4 py-3.5">
                      {isReference ? (
                        <Badge tone="blue">{t("drawings.table.reference")}</Badge>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Badge tone={getDrawingStatusTone(drawing.status)}>{formatDrawingStatus(drawing.status)}</Badge>
                          {isDrawingInProgress(drawing.status) ? (
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-trace-gold)]" />
                          ) : null}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-[12.5px] text-[var(--color-text-secondary)]">{formatFileSize(drawing.file_size_bytes)}</td>
                    <td className="px-4 py-3.5 text-right">
                      {isReference ? (
                       <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={viewFile.isPending}
                          onClick={() => viewFile.mutate(drawing.id)}
                        >
                          {viewFile.isPending ? t("drawings.table.opening") : t("drawings.table.viewPdf")}
                        </Button>
                        {canSuggestItems ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={suggestItems.isPending}
                              onClick={() => handleSuggestItems(drawing)}
                              title={t("drawings.suggest.buttonTitle")}
                            >
                              <Icon name="spark" size={12} />
                              {suggestItems.isPending ? t("drawings.suggest.reading") : t("drawings.suggest.button")}
                            </Button>
                          ) : null}
                        </div>
                      ) : (
                        <Button variant="ghost" size="sm" disabled={drawing.status !== "PARSED"} onClick={() => onView(drawing)}>
                          {t("drawings.table.viewElements")}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}