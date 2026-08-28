import type { Organization } from "../types/organization.types";
import { getOrganizationInitials } from "../utils/organization.utils";
import {Badge, Button, GlassChip, Icon, LivePip,
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
    <section className="overflow-hidden rounded-[14px] border border-[#263356] bg-[linear-gradient(120deg,#080d18_0%,#0d1424_60%,#192640_100%)] text-white shadow-[0_12px_32px_rgba(8,13,24,0.14)]">
      <div className="relative p-5 sm:p-6">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.028)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.028)_1px,transparent_1px)] bg-[length:28px_28px]" />

        <div className="pointer-events-none absolute -right-20 -top-24 h-56 w-56 rounded-full bg-[#d9a441]/[0.07] blur-3xl" />

        <div className="relative">
        
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 items-start gap-4">
        
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[11px] border border-[#d9a441]/30 bg-[linear-gradient(155deg,#d9a441,#b98626)] font-[Archivo] text-[15px] font-bold text-[#080d18] shadow-[0_6px_18px_rgba(217,164,65,0.12)]">
                {getOrganizationInitials(organization.name)}
              </div>

              <div className="min-w-0">
                <div className="mb-1.5 flex flex-wrap items-center gap-2.5">
                  <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-[#8f9bb0]">
                    Organization workspace
                  </span>

                  {organization.is_active ? (
                    <LivePip label="Active" />
                  ) : null}
                </div>

                <h1 className="truncate font-[Archivo] text-[23px] font-bold tracking-[-0.04em] text-white sm:text-[27px]">
                  {organization.name}
                </h1>

                <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-2">
                  <span className="max-w-[260px] truncate font-mono text-[10.5px] text-[#a2957c]">
                    {organization.slug}
                  </span>

                  <span className="text-[#4b5871]">·</span>

                  <Badge tone={organization.is_active ? "green" : "red"}>
                    {organization.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </div>
            </div>

            {canManage && onEdit ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={onEdit}
                className="self-start border-[#34415f] bg-[#141c30] text-white hover:border-[#465576] hover:bg-[#1b2540]"
              >
                <Icon name="edit" size={13} />
                Edit organization
              </Button>
            ) : null}
          </div>

          <div className="relative mt-5 border-t border-[#263356] pt-4">
            <div className="grid gap-2.5 sm:grid-cols-3">
              <GlassChip
                icon="building"
                label="Workspace status"
                value={
                  organization.is_active ? "Operational" : "Restricted"
                }
              />

              <GlassChip
                icon="spark"
                label="AI controls"
                value={organization.ai_enabled ? "Enabled" : "Disabled"}
              />

              <div className="min-w-0">
                <GlassChip
                  icon="key"
                  label="Workspace ID"
                  value={organization.id}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}