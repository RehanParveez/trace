import { useTranslation } from "react-i18next";
import {ErrorState, LoadingState, Modal,
} from "../../organizations/components/OrganizationUi";
import { useBOQItemTrace } from "../hooks";
import { formatJsonValue } from "../utils/drawings-boq.utils";

interface BOQItemTraceDialogProps {
  itemId: string;
  itemName: string;
  onClose: () => void;
}

export function BOQItemTraceDialog({
  itemId,
  itemName,
  onClose,
}: BOQItemTraceDialogProps) {
  const { t } = useTranslation();
  const query = useBOQItemTrace(itemId);

  return (
    <Modal
      title={t("boq.itemTrace.title", { name: itemName })}
      description={t("boq.itemTrace.description")}
      onClose={onClose}
      wide
    >
      {query.isLoading ? (
        <LoadingState label={t("boq.itemTrace.loading")} />
      ) : query.isError ? (
        <ErrorState
          title={t("boq.itemTrace.loadError")}
          onRetry={() => void query.refetch()}
        />
      ) : (
        <pre className="max-h-[65vh] overflow-auto rounded-[8px] bg-[var(--color-surface-muted)] p-4 text-[11px] leading-5 text-[var(--color-text-secondary)]">
          {formatJsonValue(query.data)}
        </pre>
      )}
    </Modal>
  );
}