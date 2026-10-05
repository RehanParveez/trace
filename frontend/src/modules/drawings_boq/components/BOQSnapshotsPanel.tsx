import { useState } from "react";
import {Badge, ErrorState, LoadingState, Panel, PanelHeader,
} from "../../organizations/components/OrganizationUi";
import {useBOQSnapshotItems, useBOQSnapshots,
} from "../hooks";
import {formatCurrency, formatQuantity,
} from "../utils/drawings-boq.utils";

interface BOQSnapshotsPanelProps {
  versionId: string;
}

export function BOQSnapshotsPanel({
  versionId,
}: BOQSnapshotsPanelProps) {
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
        <LoadingState label="Loading snapshots…" />
      </Panel>
    );
  }

  if (snapshots.isError) {
    return (
      <Panel>
        <ErrorState
          title="Couldn't load snapshots"
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
        eyebrow="IMMUTABLE RECORDS"
        title="BOQ snapshots"
        description="Immutable versioned records created for approval and issue history."
      />

      <div className="grid gap-4 p-5 lg:grid-cols-[280px_1fr]">
        <div className="space-y-2">
          {list.length === 0 ? (
            <div className="text-[12px] text-[var(--color-text-muted)]">
              No snapshots yet.
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
                    Snapshot v
                    {snapshot.version_no}
                  </span>

                  <Badge tone="slate">
                    {snapshot.purpose}
                  </Badge>
                </div>

                <div className="mt-2 text-[10.5px] text-[var(--color-text-muted)]">
                  {snapshot.item_count} items
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
              Select a snapshot to inspect its frozen line items.
            </div>
          ) : items.isLoading ? (
            <LoadingState label="Loading snapshot items…" />
          ) : items.isError ? (
            <ErrorState
              title="Couldn't load snapshot items"
              onRetry={() =>
                void items.refetch()
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left">
                <thead className="bg-[var(--color-surface-muted)]">
                  <tr>
                    {[
                      "Line",
                      "Work item",
                      "Description",
                      "Unit",
                      "Quantity",
                      "Rate",
                      "Amount",
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
