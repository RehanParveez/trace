import { useTranslation } from "react-i18next";
import { ErrorState, LoadingState, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { useSetSteelSource, useSteelFigures } from "../hooks/useSteelFigures";
import { SteelFiguresView } from "./SteelFiguresView";
import type { SteelFiguresSource } from "../types/steelFigures.types";

interface Props {
  runId: string;
  projectId: string;
  canEdit: boolean;
  wastagePct?: number | null;
}

export function SteelFiguresCard({ runId, projectId, canEdit, wastagePct = null }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const q = useSteelFigures(runId, wastagePct);
  const save = useSetSteelSource(projectId);
  if (q.isLoading) return <LoadingState label={t("steel.loading", "Loading the steel figures…")} />;
  if (q.isError || !q.data) return <ErrorState title={t("steel.error", "Couldn't load the steel figures")} onRetry={() => void q.refetch()} />;
  const choose = (source: SteelFiguresSource) => save.mutate(source, {
    onSuccess: () => showToast({ tone: "success", title: t("steel.saved", "The steel line of this project now follows {{source}}.", { source }) }),
    onError: (e) => showToast({ tone: "error", title: getApiErrorMessage(e, t("steel.saveFailed", "The steel line could not be saved")) }),
  });
  return <SteelFiguresView data={q.data} canEdit={canEdit} saving={save.isPending} onChoose={choose} />;
}
