import { NavLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { BrandMark, Icon, LivePip } from "./OrganizationUi";
import type { OrganizationIconName } from "../types/organization.types";
import { NotificationBell } from "../../notifications";
import { IDENTITY_PERMISSIONS, useAuthStore, usePermissionKeys } from "../../identity";
import { useOrganization, useInvitations } from "../hooks";
import { getInvitationStatus } from "../utils/organization.utils";

interface NavItem {
  label: string;
  to: string;
  icon: OrganizationIconName;
  exact?: boolean;
  badge?: number;
}

function buildWorkspaceNav(): NavItem[] {
  return [
    {
      label: "Overview",
      to: "/app/organization",
      icon: "dashboard",
      exact: true,
    },
  ];
}

function buildOrganizationNav(
  pendingInvitationCount?: number,
): NavItem[] {
  return [
    {
      label: "Settings",
      to: "/app/organization/settings",
      icon: "settings",
    },
    {
      label: "Members",
      to: "/app/organization/members",
      icon: "users",
    },
    {
      label: "Roles & access",
      to: "/app/organization/roles",
      icon: "shield",
    },
    {
      label: "Invitations",
      to: "/app/organization/invitations",
      icon: "mail",
      badge: pendingInvitationCount,
    },
    {
      label: "Subscription",
      to: "/app/subscription",
      icon: "budget",
    },
    {
      label: "Material library",
      to: "/app/drawings_boq",
      icon: "materials",
    },
    {
      label: "Labour rates",
      to: "/app/drawings_boq/labour-rates",
      icon: "budget",
    },
    {
      label: "WhatsApp connection",
      to: "/app/whatsapp-settings",
      icon: "external",
    },
  ];
}

function buildProjectsNav(): NavItem[] {
  return [
    {
      label: "Projects",
      to: "/app/projects",
      icon: "projects",
    },
    {
      label: "Budgets",
      to: "/app/budgets",
      icon: "budget",
    },
    {
      label: "Progress review",
      to: "/app/progress-review",
      icon: "check",
    },
    {
      label: "Site photos",
      to: "/app/site-photos",
      icon: "spark",
    },
    {
      label: "Site progress",
      to: "/app/site-logs",
      icon: "site",
    },
    {
      label: "Procurement",
      to: "/app/procurement",
      icon: "procurement",
    },
    {
      label: "Expenses",
      to: "/app/expenses",
      icon: "expenses",
    },
  ];
}

function buildIntelligenceNav(isPlatformAdmin: boolean): NavItem[] {
  return [
    {
      label: "AI activity",
      to: "/app/ai-activity",
      icon: "spark",
    },
    {
      label: "Audit log",
      to: "/app/audit-log",
      icon: "shield",
    },
    ...(isPlatformAdmin
      ? [
          {
            label: "All subscriptions",
            to: "/app/platform-admin/subscriptions",
            icon: "shield" as OrganizationIconName,
          },
        ]
      : []),
  ];
}

function SidebarLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.exact}
      className={({ isActive }) =>
        [
          "group relative flex min-h-[40px] items-center gap-3 rounded-[9px] border px-3",
          "text-[13px] font-medium transition-all duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#d9a441]/40",
          isActive
            ? "border-[#d9a441]/30 !bg-[#172239] !text-white shadow-[inset_0_0_0_1px_rgba(217,164,65,0.06)]"
            : "border-transparent !text-[#cbd5e1] hover:!border-[#263657] hover:!bg-[#121c30] hover:!text-white",
        ].join(" ")
      }
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            <span className="absolute -left-[1px] top-[7px] bottom-[7px] w-[3px] rounded-r-full bg-[#d9a441]" />
          ) : null}

          <span
            className={[
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] transition-colors",
              isActive
                ? "bg-[#d9a441]/12 text-[#e3b65a]"
                : "bg-transparent !text-[#9eacc1] group-hover:!text-[#dbe4f0]",
            ].join(" ")}
          >
            <Icon name={item.icon} size={16} />
          </span>

          <span className="min-w-0 flex-1 truncate">
            {item.label}
          </span>

          {typeof item.badge === "number" && item.badge > 0 ? (
            <span
              className={[
                "min-w-[20px] rounded-full px-1.5 py-0.5 text-center font-mono text-[10px]",
                isActive
                  ? "bg-[#d9a441]/15 text-[#e3b65a]"
                  : "bg-[#202c45] text-[#b7c3d5]",
              ].join(" ")}
            >
              {item.badge}
            </span>
          ) : null}
        </>
      )}
    </NavLink>
  );
}

export function OrganizationShell({
  children,
}: {
  children?: ReactNode;
}) {
  const permissions = usePermissionKeys();
  const isPlatformAdmin = useAuthStore(
    (state) => state.user?.is_platform_admin ?? false,
  );
  const canManageMembers = permissions.includes(
    IDENTITY_PERMISSIONS.ORGANIZATION_MEMBERS_MANAGE,
  );

  const organizationQuery = useOrganization();
  const invitationsQuery = useInvitations(0, 100, {
    enabled: canManageMembers,
  });

  const organizationName = organizationQuery.data?.name ?? "Current organization";
  const organizationSlug = organizationQuery.data?.slug;
  const pendingInvitationCount = canManageMembers
    ? invitationsQuery.data?.items.filter(
        (invitation) => getInvitationStatus(invitation) === "pending",
      ).length
    : undefined;

  const workspaceNav = buildWorkspaceNav();
  const organizationNav = buildOrganizationNav(pendingInvitationCount);
  const projectsNav = buildProjectsNav();
  const intelligenceNav = buildIntelligenceNav(isPlatformAdmin);

    return (
    <div className="min-h-screen bg-[var(--color-workspace)] text-[var(--color-text-primary)] [font-family:Inter,system-ui,sans-serif]">
      
       <a href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[200] focus:rounded-[8px] focus:bg-[var(--color-trace-gold)] focus:px-4 focus:py-2.5 focus:text-[13px] focus:font-semibold focus:text-[var(--color-trace-navy)] focus:shadow-lg"
      >
        Skip to main content
      </a>

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col overflow-hidden !border-r !border-[#24314d] !bg-[var(--color-trace-navy)] !text-[#cbd5e1] lg:flex">
        <div className="relative flex h-[94px] shrink-0 items-center overflow-hidden !border-b !border-[#24314d] !bg-[var(--color-trace-navy)] px-5">
          <div className="pointer-events-none absolute inset-0 opacity-[0.22] [background-image:linear-gradient(#53617a_1px,transparent_1px),linear-gradient(90deg,#53617a_1px,transparent_1px)] [background-size:18px_18px]" />

          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_35%,rgba(217,164,65,0.12),transparent_32%)]" />

          <div className="relative flex min-w-0 items-center gap-3">
            <BrandMark />

            <div className="min-w-0">
              <div className="font-[Archivo] text-[18px] font-semibold tracking-[-0.035em] !text-white">
                Trace
              </div>

              <div className="mt-1 truncate text-[8px] font-semibold uppercase tracking-[0.18em] !text-[#8795aa]">
                Construction Intelligence
              </div>
            </div>
          </div>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-6">
          <div className="mb-3 px-2 text-[9px] font-bold uppercase tracking-[0.18em] !text-[#78869c]">
            Workspace
          </div>

          <div className="space-y-1">
            {workspaceNav.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>

          <div className="mb-3 mt-7 px-2 text-[9px] font-bold uppercase tracking-[0.18em] !text-[#78869c]">
            Organization
          </div>

          <div className="space-y-1">
            {organizationNav.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>

          <div className="mb-3 mt-7 px-2 text-[9px] font-bold uppercase tracking-[0.18em] !text-[#78869c]">
            Projects
          </div>

          <div className="space-y-1">
            {projectsNav.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>

          <div className="mb-3 mt-7 px-2 text-[9px] font-bold uppercase tracking-[0.18em] !text-[#78869c]">
            Intelligence
          </div>

          <div className="space-y-1">
            {intelligenceNav.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>
        </nav>

        <div className="shrink-0 !border-t !border-[#24314d] !bg-[var(--color-trace-navy)] p-4">
          <div className="mb-3 px-1">
            <LivePip label="All systems synced" />
          </div>

          <div className="flex items-center gap-3 rounded-[10px] !border !border-[#202d46] !bg-[var(--color-trace-navy-soft)] p-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(155deg,#4a5b82,#2a3652)] font-[Archivo] text-[11px] font-semibold !text-white">
              OR
            </div>

            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] font-semibold !text-white">
                {organizationName}
              </div>

              <div className="mt-0.5 truncate text-[10px] !text-[#8d9bb0]">
                {organizationSlug ?? "Organization workspace"}
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex min-h-[64px] items-center gap-3 border-b border-[var(--color-border)] bg-white/95 px-4 backdrop-blur sm:px-7">
          <div className="flex min-w-0 items-center gap-2.5 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2 shadow-sm">
            <Icon name="building" size={15} className="text-[var(--color-text-muted)]" />
            <span className="max-w-[220px] truncate text-[13px] font-semibold text-[var(--color-text-primary)]">
              {organizationName}
            </span>
          </div>

      <div className="hidden h-10 max-w-[380px] flex-1 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[var(--color-text-muted)] md:flex">
       <Icon name="search" size={15} />
       <span className="text-[13px]">Search organization workspace</span>
       <span className="ml-auto rounded border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text-muted)]">
         ⌘K
       </span>
      </div>

      <div className="ml-auto flex items-center gap-3">
       <div className="hidden items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-success)] sm:flex">
        <span className="relative flex h-1.5 w-1.5">
         <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-success)] opacity-60" />
         <span className="relative h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />
      </span>
      Workspace operational
    </div>
    <NotificationBell />
    <button
      type="button"
      className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-muted)]"
      aria-label="Organization settings"
    >
      <Icon name="settings" size={16} />
    </button>
  </div>
</header>

        <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[1440px] px-4 py-7 sm:px-7 lg:px-8 focus:outline-none">
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}