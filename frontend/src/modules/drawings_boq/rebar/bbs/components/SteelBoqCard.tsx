import { useTranslation } from "react-i18next";
import { ErrorState, LoadingState, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { useApplySteelBoq, useSteelBoq } from "../hooks/useSteelBoq";
import { SteelBoqView } from "./SteelBoqView";

interface Props {
  versionId: string;
  canAdjust: boolean;
}

export function SteelBoqCard({ versionId, canAdjust }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const q = useSteelBoq(versionId);
  const apply = useApplySteelBoq(versionId);
  if (q.isLoading) return <LoadingState label={t("steelBoq.loading", "Checking the steel on the bill…")} />;
  if (q.isError || !q.data) {
    return <ErrorState title={getApiErrorMessage(q.error, t("steelBoq.error", "Couldn't check the steel on the bill"))} onRetry={() => void q.refetch()} />;
  }
  const press = () => apply.mutate(undefined, {
    onSuccess: () => showToast({ tone: "success", title: t("steelBoq.done", "The bill's steel is up to date.") }),
    onError: (e) => showToast({ tone: "error", title: getApiErrorMessage(e, t("steelBoq.failed", "The steel could not be put on the bill")) }),
  });
  return <SteelBoqView data={q.data} canAdjust={canAdjust} applying={apply.isPending} onApply={press} />;
}
