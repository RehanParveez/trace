import { ErrorState, LoadingState, PageHeader } from "../../organizations/components/OrganizationUi";
import { usePermissionKeys } from "../../identity";
import { useAIRequestLog } from "../hooks";
import { AI_REQUEST_PERMISSIONS } from "../permissions";
import { AIRequestTable } from "../components/AIRequestTable";
import { AIUsageSummaryCards } from "../components/AIUsageSummaryCards";

export function AIRequestsPage() {
  const permissions = usePermissionKeys();
  const canRead = permissions.includes(AI_REQUEST_PERMISSIONS.AI_REQUEST_READ);
  const requestsQuery = useAIRequestLog();

  if (!canRead) {
    return <ErrorState title="AI request log unavailable" description="You don't have permission to view this organization's AI activity." />;
  }
  if (requestsQuery.isLoading) return <LoadingState label="Loading AI requests…" />;
  if (requestsQuery.isError) return <ErrorState title="Couldn't load AI requests" onRetry={() => void requestsQuery.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader title="AI activity" description="Every AI call made on behalf of this organization — material normalization, caption parsing, and their outcomes." />
      <AIUsageSummaryCards />
      <AIRequestTable entries={requestsQuery.data ?? []} />
    </div>
  );
}