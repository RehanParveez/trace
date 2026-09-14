import { ErrorState, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { useAIRequestLog } from "../hooks";
import { AI_REQUEST_PERMISSIONS } from "../permissions";
import { AIRequestTable } from "../components/AIRequestTable";
import { AIUsageSummaryCards } from "../components/AIUsageSummaryCards";
import { useTranslation } from "react-i18next";

export function AIRequestsPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(AI_REQUEST_PERMISSIONS.AI_REQUEST_READ);
  const { t } = useTranslation();
  const requestsQuery = useAIRequestLog();

  if (!canRead) {
    return <ErrorState title={t("ai.page.accessUnavailable")} description={t("ai.page.accessUnavailableDesc")} />;
  }
  if (requestsQuery.isLoading) return <LoadingState label={t("ai.page.loading")} />;
  if (requestsQuery.isError) return <ErrorState title={t("ai.page.loadError")} onRetry={() => void requestsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader eyebrow={t("ai.page.eyebrow")} title={t("ai.page.title")} description={t("ai.page.description")}
    />
      <AIUsageSummaryCards />
      <AIRequestTable entries={requestsQuery.data ?? []} />
    </div>
  );
}