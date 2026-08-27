import type {Organization,
} from "../types/organization.types";
import {Badge, Button, Icon,
} from "./OrganizationUi";

interface OrganizationHeaderProps {
  organization: Organization;
  onEdit?: () => void;
  canManage?: boolean;
}

export function OrganizationHeader({
  organization,
  onEdit,
  canManage = false,
}: OrganizationHeaderProps) {
  return (
    <div className="overflow-hidden rounded-[16px] border border-[#263356] bg-[linear-gradient(120deg,#080d18_0%,#0d1424_58%,#1b2842_100%)] text-white shadow-[0_10px_30px_rgba(8,13,24,0.12)]">
      <div className="relative px-5 py-5 sm:px-6 sm:py-6">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[length:26px_26px]" />

        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="flex min-w-0 items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] bg-[linear-gradient(155deg,#d9a441,#b98626)] text-[#080d18] shadow-sm">
              <Icon
                name="building"
                size={20}
              />
            </div>

            <div className="min-w-0">
              <div className="mb-1 text-[9px] font-bold uppercase tracking-[0.18em] text-[#a2957c]">
                Organization workspace
              </div>

              <h1 className="truncate font-[Archivo] text-[24px] font-bold tracking-[-0.04em] text-white sm:text-[28px]">
                {organization.name}
              </h1>

              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[#a2957c]">
                <span>
                  {organization.slug}
                </span>

                <span className="text-[#4b5871]">
                  ·
                </span>

                <Badge
                  tone={
                    organization.is_active
                      ? "green"
                      : "red"
                  }
                >
                  {organization.is_active
                    ? "Active"
                    : "Inactive"}
                </Badge>
              </div>
            </div>
          </div>

          {canManage && onEdit ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={onEdit}
              className="border-[#263356] bg-[#141c30] text-white hover:bg-[#1b2540]"
            >
              <Icon
                name="edit"
                size={13}
              />
              Edit organization
            </Button>
          ) : null}
        </div>

        <div className="relative mt-5 grid gap-4 border-t border-[#263356] pt-4 sm:grid-cols-3">
          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.13em] text-[#71809b]">
              Workspace status
            </div>

            <div className="mt-1 text-[12px] font-semibold text-white">
              {organization.is_active
                ? "Operational"
                : "Restricted"}
            </div>
          </div>

          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.13em] text-[#71809b]">
              AI controls
            </div>

            <div className="mt-1 text-[12px] font-semibold text-white">
              {organization.ai_enabled
                ? "Enabled by organization"
                : "Disabled by organization"}
            </div>
          </div>

          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.13em] text-[#71809b]">
              Workspace ID
            </div>

            <div className="mt-1 truncate font-mono text-[10px] text-[#a2957c]">
              {organization.id}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}