import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { LoadingState, useToast } from "../../organizations/components/OrganizationUi";
import { useDatums, useSaveDatums } from "../hooks/useDatums";
import { useElementParameters, useSaveElementParameters } from "../hooks/useElementParams";
import type { RunStats } from "../types/drawings-boq.types";
import { datumDraft, datumUpdate, elementDraft, elementRows, elementUpdate } from "../utils/levels";
import { BalanceBlock, BandsList, DatumEditor, DpcBlock, ElementEditor } from "./StagesView";

export function StagesPanel({ projectId, stats, canEdit = true }: { projectId: string; stats?: RunStats; canEdit?: boolean }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const datums = useDatums(projectId);
  const saveDatums = useSaveDatums(projectId);
  const elements = useElementParameters(projectId);
  const saveElements = useSaveElementParameters(projectId);
  const [datumBoxes, setDatumBoxes] = useState<Record<string, string>>({});
  const [elementBoxes, setElementBoxes] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    if (datums.data) setDatumBoxes(datumDraft(datums.data.datums));
  }, [datums.data]);
  useEffect(() => {
    if (elements.data) setElementBoxes(elementDraft(elements.data.values));
  }, [elements.data]);

  const rows = useMemo(() => elementRows(stats?.derived?.foundation_list, elements.data?.labels ?? {}), [stats, elements.data]);

  function onSaveDatums() {
    if (!datums.data) return;
    const { values, errors } = datumUpdate(datumBoxes, datums.data.datums);
    if (errors.length > 0) return;
    if (Object.keys(values).length === 0) {
      showToast({ tone: "success", title: t("boq.levels.nothingToSave", "Nothing changed") });
      return;
    }
    saveDatums.mutate(values, {
      onSuccess: () => showToast({ tone: "success", title: t("boq.levels.savedToast", "Levels saved. Run the calculation again to use them.") }),
      onError: () => showToast({ tone: "error", title: t("boq.levels.saveFailed", "The levels were not saved") }),
    });
  }

  function onSaveElements() {
    if (!elements.data) return;
    const { values, labels, errors } = elementUpdate(elementBoxes, elements.data.values, rows, elements.data.ranges);
    if (errors.length > 0) return;
    if (Object.keys(values).length === 0) {
      showToast({ tone: "success", title: t("boq.levels.nothingToSave", "Nothing changed") });
      return;
    }
    saveElements.mutate({ values, labels }, {
      onSuccess: () => showToast({ tone: "success", title: t("boq.levels.elementsSavedToast", "Footing values saved. Run the calculation again to use them.") }),
      onError: () => showToast({ tone: "error", title: t("boq.levels.saveFailed", "The values were not saved") }),
    });
  }

  if (datums.isLoading) return <div className="p-4"><LoadingState label={t("boq.levels.loading", "Loading levels")} /></div>;

  return (
    <div data-testid="stages-panel" className="space-y-3 p-4">
      <BandsList stats={stats} />
      <DatumEditor
        datums={datums.data?.datums ?? []}
        typed={datums.data?.typed ?? {}}
        draft={datumBoxes}
        onDraft={setDatumBoxes}
        onSave={onSaveDatums}
        saving={saveDatums.isPending}
        canEdit={canEdit}
      />
      <BalanceBlock stats={stats} />
      <DpcBlock stats={stats} />
      <ElementEditor
        stats={stats}
        labels={elements.data?.labels ?? {}}
        ranges={elements.data?.ranges ?? {}}
        draft={elementBoxes}
        onDraft={setElementBoxes}
        onSave={onSaveElements}
        saving={saveElements.isPending}
        canEdit={canEdit}
      />
    </div>
  );
}
