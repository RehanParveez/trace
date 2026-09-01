import { NavLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { BrandMark, Icon, LivePip } from "./OrganizationUi";
import type { OrganizationIconName } from "../types/organization.types";
import { NotificationBell } from "../../notifications";

interface OrganizationShellProps {
  children?: ReactNode;
  organizationName?: string;
  organizationSlug?: string;
  pendingInvitationCount?: number;
}

interface NavItem {
  label: string;
  to: string;
  icon: OrganizationIconName;
  exact?: boolean;
  badge?: number;
}

function buildOrganizationNav(
  pendingInvitationCount?: number,
): NavItem[] {
  return [
    {
      label: "Overview",
      to: "/app/organization",
      icon: "dashboard",
      exact: true,
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
      label: "Material library",
      to: "/app/drawings_boq",
      icon: "materials",
    },
  ];
}

const productNav: NavItem[] = [
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

function SidebarLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.exact}
      className={({ isActive }) =>
        [
          "group relative flex min-h-[40px] items-center gap-3 rounded-[9px] border px-3",
          "text-[13px] font-medium transition-all duration-150",
          "focus:outline-none focus:ring-2 focus:ring-[#d9a441]/40",
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
  organizationName = "Current organization",
  organizationSlug,
  pendingInvitationCount,
}: OrganizationShellProps) {
  const organizationNav = buildOrganizationNav(
    pendingInvitationCount,
  );

  return (
    <div className="min-h-screen bg-[#f5efe3] text-[#191410] [font-family:Inter,system-ui,sans-serif]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col overflow-hidden !border-r !border-[#24314d] !bg-[#080d18] !text-[#cbd5e1] lg:flex">
        <div className="relative flex h-[94px] shrink-0 items-center overflow-hidden !border-b !border-[#24314d] !bg-[#080d18] px-5">
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
            {organizationNav.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>

          <div className="mb-3 mt-7 px-2 text-[9px] font-bold uppercase tracking-[0.18em] !text-[#78869c]">
            Project data
          </div>

          <div className="space-y-1">
            {productNav.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>
        </nav>

        <div className="shrink-0 !border-t !border-[#24314d] !bg-[#080d18] p-4">
          <div className="mb-3 px-1">
            <LivePip label="All systems synced" />
          </div>

          <div className="flex items-center gap-3 rounded-[10px] !border !border-[#202d46] !bg-[#0d1525] p-2.5">
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
        <header className="sticky top-0 z-30 flex min-h-[64px] items-center gap-3 !border-b !border-[#e1d5bc] !bg-white/95 px-4 backdrop-blur sm:px-7">
          <div className="flex min-w-0 items-center gap-2 rounded-[9px] !border !border-[#e1d5bc] !bg-[#fbf8f2] px-3 py-2">
            <Icon
              name="building"
              size={14}
              className="text-[#8b7350]"
            />

            <span className="max-w-[220px] truncate text-[12px] font-semibold !text-[#332a21]">
              {organizationName}
            </span>
          </div>

          <div className="hidden h-9 max-w-[380px] flex-1 items-center gap-2 rounded-[9px] !border !border-[#e1d5bc] !bg-[#fbf8f2] px-3 !text-[#a2957c] md:flex">
            <Icon name="search" size={14} />

            <span className="text-[12px]">
              Search organization workspace
            </span>

            <span className="ml-auto rounded border border-[#e1d5bc] bg-white px-1.5 py-0.5 font-mono text-[9px] !text-[#8c806e]">
              ⌘K
            </span>
          </div>

          <div className="ml-auto flex items-center gap-3">
           <div className="hidden items-center gap-2 text-[9px] font-bold uppercase tracking-[0.16em] !text-[#668165] sm:flex">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#1e9d63] opacity-60" />
              <span className="relative h-1.5 w-1.5 rounded-full bg-[#1e9d63]" />
            </span>

            Workspace operational
            </div>

            <NotificationBell />

            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-[9px] !border !border-[#e1d5bc] !bg-white !text-[#6b6152] transition hover:!bg-[#f5efe3]"
              aria-label="Organization settings"
            >
             <Icon name="settings" size={15} />
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-7 lg:px-8">
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}