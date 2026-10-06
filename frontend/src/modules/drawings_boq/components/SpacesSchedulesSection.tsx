import { useState } from "react";
import { Panel } from "../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../identity";
import type { Drawing } from "../types/drawings-boq.types";
import { ScheduleImportsPanel } from "./ScheduleImportsPanel";
import { SpacesPanel } from "./SpacesPanel";
import { useTranslation } from "react-i18next";

interface SpacesSchedulesSectionProps {
  projectId: string;
  drawings: Drawing[];
}

export function SpacesSchedulesSection({ projectId, drawings }: SpacesSchedulesSectionProps) {
  const { t } = useTranslation();
  const permissions = usePermissionKeys();
  const [tab, setTab] = useState<"spaces" | "schedules">("spaces");

  if (!permissions.includes(IDENTITY_PERMISSIONS.DRAWING_READ)) return null;
  const canManageSpaces = permissions.includes(IDENTITY_PERMISSIONS.SPACE_MANAGE);
  const canManageFinish = permissions.includes(IDENTITY_PERMISSIONS.FINISH_MANAGE);
  const canImport = permissions.includes(IDENTITY_PERMISSIONS.SCHEDULE_IMPORT);

  const tabCls = (a: boolean) =>
    `rounded-[7px] border px-3 py-1.5 text-[12px] font-semibold transition ${a ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]" : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]"}`;

  return (
    <div className="space-y-5">
      <Panel className="flex gap-2 p-4">
        <button type="button" className={tabCls(tab === "spaces")} onClick={() => setTab("spaces")}>{t("section.spaces", "Spaces and finishes")}</button>
        <button type="button" className={tabCls(tab === "schedules")} onClick={() => setTab("schedules")}>{t("section.schedules", "Schedules")}</button>
      </Panel>
      {tab === "spaces" ? (
        <SpacesPanel projectId={projectId} drawings={drawings} canManage={canManageSpaces} canManageFinish={canManageFinish} />
      ) : (
        <ScheduleImportsPanel projectId={projectId} drawings={drawings} canImport={canImport} canManageSpaces={canManageSpaces} />
      )}
    </div>
  );
}
