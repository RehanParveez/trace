import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {Button,EmptyState,ErrorState, LoadingState, Modal, Badge,
} from "../../organizations/components/OrganizationUi";
import {useDrawingElementsPage, useDrawingLevels,
} from "../hooks";
import type {Drawing, DrawingElement, NormalizationStatus,
} from "../types/drawings-boq.types";
import {formatQuantity, elementMeasureMode,
} from "../utils/drawings-boq.utils";

interface DrawingElementsDialogProps {
  drawing: Drawing;
  onClose: () => void;
}

export function DrawingElementsDialog({
  drawing,
  onClose,
}: DrawingElementsDialogProps) {
  const { t } = useTranslation();
  const [structuralRole, setStructuralRole] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [levelId, setLevelId] = useState("");
  const [normalizationStatus, setNormalizationStatus] = useState<NormalizationStatus | "">("");
  const [after, setAfter] = useState<string | null>(null);
  const elementsQuery =
    useDrawingElementsPage(
      drawing.id,
      {
        limit: 1000,
        cursor: after,
        structural_role:
          structuralRole.trim() || null,
        discipline:
          discipline.trim() || null,
        level_id:
          levelId || null,
        normalization_status:
          normalizationStatus || null,
      },
    );

    
  const levelsQuery =
    useDrawingLevels(drawing.id);

  const [items, setItems] = useState<DrawingElement[]>([]);

  useEffect(() => {
    const page = elementsQuery.data?.items;
    if (!page) return;
    setItems((previous) => {
      if (after === null) return page;
      const seen = new Set(previous.map((element) => element.id));
      return [...previous, ...page.filter((element) => !seen.has(element.id))];
    });
  }, [elementsQuery.data, after]);

  const levelNames = useMemo(
    () => new Map((levelsQuery.data ?? []).map((level) => [level.id, level.name])),
    [levelsQuery.data],
  );
  const total = elementsQuery.data?.total ?? null;

  return (
    <Modal
      title={drawing.original_filename}
      onClose={onClose}
    >
      <div className="space-y-4">
        <p className="text-[12px] text-[var(--color-text-muted)]">
          {t("drawings.elements.description")}
        </p>

        <div className="flex flex-wrap gap-2">
          <input
            value={structuralRole}
            onChange={(event) => {
              setStructuralRole(
                event.target.value,
              );
              setAfter(null);
            }}
            placeholder={t(
              "drawings.elements.structuralRole",
            )}
            aria-label={t(
              "drawings.elements.structuralRole",
            )}
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
            placeholder={t(
              "drawings.elements.discipline",
            )}
            aria-label={t(
              "drawings.elements.discipline",
            )}
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
            aria-label={t(
              "drawings.elements.level",
            )}
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
          >
            <option value="">
              {t("drawings.elements.allLevels")}
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
            value={normalizationStatus}
            onChange={(event) => {
              setNormalizationStatus(
                event.target.value as
                  | NormalizationStatus
                  | "",
              );
              setAfter(null);
            }}
            aria-label={t(
              "drawings.elements.normalization",
            )}
            className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
          >
            <option value="">
              {t(
                "drawings.elements.allNormalizationStates",
              )}
            </option>

            <option value="PENDING">
              {t("drawings.elements.pending")}
            </option>

            <option value="VALID">
              {t("drawings.elements.valid")}
            </option>

            <option value="WARNING">
              {t("drawings.elements.warning")}
            </option>

            <option value="INVALID">
              {t("drawings.elements.invalid")}
            </option>
          </select>
        </div>

        {elementsQuery.isLoading && items.length === 0 ? (
          <LoadingState
            label={t(
              "drawings.elements.loading",
            )}
          />
        ) : elementsQuery.isError ? (
          <ErrorState
            title={t(
              "drawings.elements.errorTitle",
            )}
            onRetry={() =>
              void elementsQuery.refetch()
            }
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon="info"
            title={t(
              "drawings.elements.emptyTitle",
            )}
            description={t(
              "drawings.elements.emptyDescription",
            )}
          />
        ) : (
          <div className="max-h-[60vh] overflow-auto">
            <table className="w-full min-w-[1100px] text-left">
              <thead className="sticky top-0 bg-[var(--color-surface-muted)]">
                <tr>
                  {[
                    {
                      key: "ifcType",
                      label: t(
                        "drawings.elements.ifcType",
                      ),
                    },
                    {
                      key: "name",
                      label: t(
                        "drawings.elements.name",
                      ),
                    },
                    {
                      key: "role",
                      label: t(
                        "drawings.elements.role",
                      ),
                    },
                    {
                      key: "discipline",
                      label: t(
                        "drawings.elements.discipline",
                      ),
                    },
                    {
                      key: "level",
                      label: t(
                        "drawings.elements.level",
                      ),
                    },
                    {
                      key: "material",
                      label: t(
                        "drawings.elements.material",
                      ),
                    },
                    {
                      key: "quantity",
                      label: t(
                        "drawings.elements.quantity",
                      ),
                    },
                    {
                      key: "normalization",
                      label: t(
                        "drawings.elements.normalization",
                      ),
                    },
                    
                    {
                      key: "measured",
                      label: t(
                        "drawings.elements.measuredAs",
                        "Measured as",
                      ),
                    },

                  ].map((header) => (
                    <th
                      key={header.key}
                      className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"
                    >
                      {header.label}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {items.map((element) => (
                  <tr
                    key={element.id}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-3 py-2.5 font-mono text-[11px]">
                      {element.ifc_type}
                    </td>

                    <td className="px-3 py-2.5 text-[12px]">
                      {element.name ?? "—"}
                    </td>

                    <td className="px-3 py-2.5 text-[11px]">
                      {element.structural_role ?? "—"}
                      {element.predefined_type && element.predefined_type !== element.structural_role
                        ? ` (${element.predefined_type})`
                        : ""}
                    </td>

                    <td className="px-3 py-2.5 text-[11px]">
                      {element.discipline ?? "—"}
                    </td>

                    <td className="px-3 py-2.5 text-[11px]">
                      {element.level_name
                        ?? (element.level_id ? levelNames.get(element.level_id) : undefined)
                        ?? "—"}
                    </td>

                    <td className="px-3 py-2.5 text-[11px]">
                      {element.raw_material_text ?? "—"}
                    </td>

                    <td className="px-3 py-2.5 font-mono text-[11px]">
                      {formatQuantity(element.quantity)}{" "}
                      {element.unit ?? ""}
                    </td>

                    <td className="px-3 py-2.5 text-[10px]">
                      {element.normalization_status ?? "—"}
                    </td>

                    <td className="px-3 py-2.5 text-[10px]">
                      {(() => {
                      const mode = elementMeasureMode(element);
                      return mode === null ? "—" : (
                        <div title={element.measured_as ?? undefined}>
                          <Badge tone={mode === "EXACT" ? "green" : mode === "APPROXIMATE" ? "gold" : "red"}>
                            {mode === "EXACT" ? "Exact" : mode === "APPROXIMATE" ? "Bbox" : "No geometry"}
                          </Badge>
                          {element.measured_as ? (
                            <div className="mt-1 text-[10px] text-[var(--color-text-muted)]">
                              {element.measured_as}
                            </div>
                          ) : null}
                        </div>
                       );
                      })()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {items.length > 0 ? (
          <p className="text-[11px] text-[var(--color-text-muted)]">
            {total !== null ? `Showing ${items.length} of ${total} elements` : `Showing ${items.length} elements`}
          </p>
        ) : null}

        {elementsQuery.data?.nextCursor ? (
          <div className="flex justify-end border-t border-[var(--color-border)] pt-3">
            <Button
              variant="ghost"
              size="sm"
              disabled={elementsQuery.isFetching}
              onClick={() =>
                setAfter(
                  elementsQuery.data?.nextCursor ?? null,
                )
              }
            >
              {t("drawings.elements.loadMore")}
            </Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}