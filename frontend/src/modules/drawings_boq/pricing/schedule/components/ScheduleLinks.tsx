import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../../../organizations/components/OrganizationUi";
import { RATE_IMPORTS_PATH } from "../utils/schedules.utils";

export function ScheduleLinks({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <Button variant="secondary" size="sm" onClick={() => navigate(RATE_IMPORTS_PATH)}>
      {canManage ? t("schedules.links.import", "Import a schedule") : t("schedules.links.view", "Schedule imports")}
    </Button>
  );
}
