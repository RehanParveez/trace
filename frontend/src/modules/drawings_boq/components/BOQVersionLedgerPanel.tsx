import { useState } from "react";
import { useTranslation } from "react-i18next";
import {ErrorState, LoadingState, Panel, PanelHeader, Button,
} from "../../organizations/components/OrganizationUi";
import { useBOQVersionLedger } from "../hooks";
import {formatQuantity,
} from "../utils/drawings-boq.utils";
import type { LedgerRowResponse } from "../types/drawings-boq.types"; 

interface BOQVersionLedgerPanelProps {
  versionId: string;
}

export function BOQVersionLedgerPanel({
  versionId,
}: BOQVersionLedgerPanelProps) {
  const { t } = useTranslation();

  const [after, setAfter] =
    useState<string | null>(null);

  const query =
    useBOQVersionLedger(
      versionId,
      {
        limit: 100,
        after,
      },
    );

  if (query.isLoading) {
    return (
      <Panel>
        <LoadingState label={t("boq.ledger.loading")} />
      </Panel>
    );
  }

  if (query.isError) {
    return (
      <Panel>
        <ErrorState
          title={t("boq.ledger.loadError")}
          onRetry={() =>
            void query.refetch()
          }
        />
      </Panel>
    );
  }

  const rows = query.data?.items ?? [];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("boq.ledger.eyebrow")}
        title={t("boq.ledger.title")}
        description={t("boq.ledger.description")}
      />

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left">
          <thead className="bg-[var(--color-surface-muted)]">
            <tr>
              {[
                "boq.ledger.colWorkItem",
                "boq.ledger.colQuantity",
                "boq.ledger.colUnit",
                "boq.ledger.colSource",
                "boq.ledger.colConfidence",
                "boq.ledger.colFormula",
              ].map((header) => (
                <th
                  key={header}
                  className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"
                >
                  {t(header)}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row: LedgerRowResponse) => (
             <tr
              key={row.id}
              className="border-t border-[var(--color-border)]"
             >
              <td className="px-4 py-3 text-[12px] font-semibold text-[var(--color-text-primary)]">
                {row.work_item_code}
              </td>

              <td className="px-4 py-3 font-mono text-[12px]">
                {formatQuantity(row.quantity_net)}
              </td>

                <td className="px-4 py-3 text-[12px]">
                  {row.unit}
                </td>

                <td className="px-4 py-3 text-[12px]">
                  {row.source_kind}
                </td>

                <td className="px-4 py-3 font-mono text-[12px]">
                  {formatQuantity(
                    row.confidence,
                  )}
                </td>

                <td className="px-4 py-3 text-[12px]">
                  {row.formula_code}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {query.data?.nextCursor ? (
          <div className="border-t border-[var(--color-border)] p-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setAfter(
                  query.data?.nextCursor ??
                    null,
                )
              }
            >
              {t("boq.ledger.loadMore")}
            </Button>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}