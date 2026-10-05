import { useState } from "react";
import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
} from "../../organizations/components/OrganizationUi";
import {
  useDrawingElementsPage,
  useDrawingLevels,
} from "../hooks";
import type {
  Drawing,
  NormalizationStatus,
} from "../types/drawings-boq.types";
import {
  formatQuantity,
} from "../utils/drawings-boq.utils";

interface DrawingElementsDialogProps {
  drawing: Drawing;
  onClose: () => void;
}

export function DrawingElementsDialog({
  drawing,
  onClose,
}: DrawingElementsDialogProps) {
  const [structuralRole, setStructuralRole] =
    useState("");

  const [discipline, setDiscipline] =
    useState("");

  const [levelId, setLevelId] =
    useState("");

  const [normalizationStatus, setNormalizationStatus] =
    useState<
      NormalizationStatus | ""
    >("");

  const [after, setAfter] =
    useState<string | null>(null);

  const elementsQuery =
    useDrawingElementsPage(
      drawing.id,
      {
        limit: 200,
        cursor: after,
        structural_role:
          structuralRole.trim() ||
          null,
        discipline:
          discipline.trim() ||
          null,
        level_id:
          levelId || null,
        normalization_status:
          normalizationStatus ||
          null,
      },
    );

  const levelsQuery =
    useDrawingLevels(
      drawing.id,
    );

  const items =
    elementsQuery.data?.items ?? [];

  return (
    <Modal
      title={drawing.original_filename}
      description="Elements extracted and normalized by the drawing intelligence pipeline."
      onClose={onClose}
      wide
    >
      <div className="space-y-4">
        <div className="grid gap-3 border-b border-[var(--color-border)] pb-4 md:grid-cols-2 lg:grid-cols-4">
          <input
            value={structuralRole}
            onChange={(event) => {
              setStructuralRole(
                event.target.value,
              );
              setAfter(null);
            }}
            placeholder="Structural role"
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
          />

          <input
            value={discipline}
            onChange={(event) => {
              setDiscipline(
                event.target.value,
              );
              setAfter(null);
            }}
            placeholder="Discipline"
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
          />

          <select
            value={levelId}
            onChange={(event) => {
              setLevelId(
                event.target.value,
              );
              setAfter(null);
            }}
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
          >
            <option value="">
              All levels
            </option>

            {(levelsQuery.data ?? []).map(
              (level) => (
                <option
                  key={level.id}
                  value={level.id}
                >
                  {level.name}
                </option>
              ),
            )}
          </select>

          <select
            value={
              normalizationStatus
            }
            onChange={(event) => {
              setNormalizationStatus(
                event.target.value as
                  | NormalizationStatus
                  | "",
              );
              setAfter(null);
            }}
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
          >
            <option value="">
              All normalization states
            </option>
            <option value="PENDING">
              Pending
            </option>
            <option value="VALID">
              Valid
            </option>
            <option value="WARNING">
              Warning
            </option>
            <option value="INVALID">
              Invalid
            </option>
          </select>
        </div>

        {elementsQuery.isLoading ? (
          <LoadingState label="Loading elements…" />
        ) : elementsQuery.isError ? (
          <ErrorState
            title="Couldn't load elements"
            onRetry={() =>
              void elementsQuery.refetch()
            }
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon="info"
            title="No elements found"
            description="No elements match the selected filters."
          />
        ) : (
          <div className="max-h-[60vh] overflow-auto">
            <table className="w-full min-w-[1100px] text-left">
              <thead className="sticky top-0 bg-[var(--color-surface-muted)]">
                <tr>
                  {[
                    "IFC type",
                    "Name",
                    "Role",
                    "Discipline",
                    "Level",
                    "Material",
                    "Quantity",
                    "Normalization",
                  ].map((header) => (
                    <th
                      key={header}
                      className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {items.map(
                  (element) => (
                    <tr
                      key={element.id}
                      className="border-t border-[var(--color-border)]"
                    >
                      <td className="px-3 py-2.5 font-mono text-[11px]">
                        {element.ifc_type}
                      </td>

                      <td className="px-3 py-2.5 text-[12px]">
                        {element.name ??
                          "—"}
                      </td>

                      <td className="px-3 py-2.5 text-[11px]">
                        {element.structural_role ??
                          "—"}
                      </td>

                      <td className="px-3 py-2.5 text-[11px]">
                        {element.discipline ??
                          "—"}
                      </td>

                      <td className="px-3 py-2.5 text-[11px]">
                        {element.level_id
                          ? element.level_id.slice(
                              0,
                              8,
                            )
                          : "—"}
                      </td>

                      <td className="px-3 py-2.5 text-[11px]">
                        {element.raw_material_text ??
                          "—"}
                      </td>

                      <td className="px-3 py-2.5 font-mono text-[11px]">
                        {formatQuantity(
                          element.quantity,
                        )}{" "}
                        {element.unit ??
                          ""}
                      </td>

                      <td className="px-3 py-2.5 text-[10px]">
                        {element.normalization_status ??
                          "—"}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}

        {elementsQuery.data
          ?.nextCursor ? (
          <div className="flex justify-end border-t border-[var(--color-border)] pt-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setAfter(
                  elementsQuery.data
                    ?.nextCursor ??
                    null,
                )
              }
            >
              Load more
            </Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}