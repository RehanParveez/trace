import { useState } from "react";
import { useTranslation } from "react-i18next";
import {Badge, ErrorState, LoadingState, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {useBOQSnapshotItems, useBOQSnapshots,
} from "../hooks";
import {formatCurrency, formatQuantity,
} from "../utils/drawings-boq.utils";
import { RateSourceBadge } from "../pricing/components/RateSourceBadge";
import { formatFactor } from "../pricing/utils/pricing.utils";

interface BOQSnapshotsPanelProps {
  versionId: string;
}

export function BOQSnapshotsPanel({
  versionId,
}: BOQSnapshotsPanelProps) {
  const { t } = useTranslation();
  const snapshots =
    useBOQSnapshots(versionId);

  const [selectedId, setSelectedId] = useState<string | undefined>();

  const items =
    useBOQSnapshotItems(
      selectedId,
    );

  if (snapshots.isLoading) {
    return (
      <Panel>
        <LoadingState label={t("boq.snapshots.loading")} />
      </Panel>
    );
  }

  if (snapshots.isError) {
    return (
      <Panel>
        <ErrorState
          title={t("boq.snapshots.loadError")}
          onRetry={() =>
            void snapshots.refetch()
          }
        />
      </Panel>
    );
  }

  const list = snapshots.data ?? [];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.snapshots.eyebrow")}
        title={t("boq.snapshots.title")}
        description={t("boq.snapshots.description")}
      />

      <div className="grid gap-4 p-5 lg:grid-cols-[280px_1fr]">
        <div className="space-y-2">
          {list.length === 0 ? (
            <div className="text-[12px] text-[var(--color-text-muted)]">
              {t("boq.snapshots.empty")}
            </div>
          ) : (
            list.map((snapshot) => (
              <button
                key={snapshot.id}
                type="button"
                onClick={() =>
                  setSelectedId(
                    snapshot.id,
                  )
                }
                className={`w-full rounded-[8px] border p-3 text-left ${
                  selectedId ===
                  snapshot.id
                    ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)]"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-semibold">
                    {t("boq.snapshots.version", {
                      version: snapshot.version_no,
                    })}
                  </span>

                  <Badge tone="slate">
                    {snapshot.purpose}
                  </Badge>
                </div>

                <div className="mt-2 text-[10.5px] text-[var(--color-text-muted)]">
                  {t("boq.snapshots.itemCount", {
                    count: snapshot.item_count,
                  })}
                </div>

                <div className="mt-1 truncate font-mono text-[9px] text-[var(--color-text-muted)]">
                  {snapshot.content_hash}
                </div>
              </button>
            ))
          )}
        </div>

        <div>
          {!selectedId ? (
            <div className="rounded-[8px] border border-dashed border-[var(--color-border)] p-8 text-center text-[12px] text-[var(--color-text-muted)]">
              {t("boq.snapshots.selectPrompt")}
            </div>
          ) : items.isLoading ? (
            <LoadingState label={t("boq.snapshots.itemsLoading")} />
          ) : items.isError ? (
            <ErrorState
              title={t("boq.snapshots.itemsLoadError")}
              onRetry={() =>
                void items.refetch()
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1000px] text-left">
                <thead className="bg-[var(--color-surface-muted)]">
                  <tr>
                    {[
                      t("boq.snapshots.colLine"),
                      t("boq.snapshots.colWorkItem"),
                      t("boq.snapshots.colDescription"),
                      t("boq.snapshots.colUnit"),
                      t("boq.snapshots.colQuantity"),
                      t("boq.snapshots.colRate"),
                      t("boq.snapshots.colSource", "Rate source"),
                      t("boq.snapshots.colAmount"),
                    ].map((header) => (
                      <th
                        key={header}
                        className="px-3 py-3 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {(items.data ?? []).map(
                    (item) => (
                      <tr
                        key={item.id}
                        className="border-t border-[var(--color-border)]"
                      >
                        <td className="px-3 py-3 font-mono text-[11px]">
                          {item.line_no}
                        </td>

                        <td className="px-3 py-3 text-[12px] font-semibold">
                          {item.work_item_code ??
                            item.material_name}
                        </td>

                        <td className="px-3 py-3 text-[11.5px] text-[var(--color-text-secondary)]">
                          {item.description ??
                            item.material_name}
                        </td>

                        <td className="px-3 py-3 text-[11px]">
                          {item.unit}
                        </td>

                        <td className="px-3 py-3 font-mono text-[11px]">
                          {formatQuantity(
                            item.quantity,
                          )}
                        </td>

                        <td className="px-3 py-3 font-mono text-[11px]">
                          {formatCurrency(
                            item.unit_rate ??
                              null,
                          )}
                        </td>

                        <td className="px-3 py-3 text-[11px]">
                          <RateSourceBadge
                            source={item.rate_source ?? null}
                            hasRate={item.unit_rate !== null && item.unit_rate !== undefined}
                          />
                          {item.base_rate !== null &&
                          item.base_rate !== undefined &&
                          item.escalation_factor !== null &&
                          item.escalation_factor !== undefined ? (
                            <div className="mt-1 font-mono text-[10px] text-[var(--color-text-muted)]">
                              {formatCurrency(item.base_rate)} {formatFactor(item.escalation_factor)}
                            </div>
                          ) : null}
                        </td>

                        <td className="px-3 py-3 font-mono text-[11px] font-semibold">
                          {formatCurrency(
                            item.amount ??
                              null,
                          )}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}