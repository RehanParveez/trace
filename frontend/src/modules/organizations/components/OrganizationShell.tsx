import {NavLink, Outlet, useLocation,
} from "react-router-dom";
import type { ReactNode } from "react";
import {BrandMark, Icon,
} from "./OrganizationUi";
import type {OrganizationIconName,
} from "../types/organization.types";

interface OrganizationShellProps {
  children?: ReactNode;
  organizationName?: string;
  organizationSlug?: string;
}

const organizationNav = [
  {
    label: "Overview",
    to: "/app/organization",
    icon: "dashboard" as OrganizationIconName,
    exact: true,
  },
  {
    label: "Members",
    to: "/app/organization/members",
    icon: "users" as OrganizationIconName,
  },
  {
    label: "Roles & access",
    to: "/app/organization/roles",
    icon: "shield" as OrganizationIconName,
  },
  {
    label: "Invitations",
    to: "/app/organization/invitations",
    icon: "mail" as OrganizationIconName,
  },
];

const productNav = [
  {
    label: "Projects",
    to: "/app/projects",
    icon: "projects" as OrganizationIconName,
  },
  {
    label: "Budgets",
    to: "/app/budgets",
    icon: "budget" as OrganizationIconName,
  },
  {
    label: "Site progress",
    to: "/app/site-logs",
    icon: "site" as OrganizationIconName,
  },
  {
    label: "Procurement",
    to: "/app/procurement",
    icon: "procurement" as OrganizationIconName,
  },
  {
    label: "Expenses",
    to: "/app/expenses",
    icon: "expenses" as OrganizationIconName,
  },
];

function SidebarLink({
  item,
}: {
  item: {
    label: string;
    to: string;
    icon: OrganizationIconName;
    exact?: boolean;
  };
}) {
  return (
    <NavLink
      to={item.to}
      end={item.exact}
      className={({ isActive }) =>
        `group relative flex items-center gap-2.5 rounded-[8px] px-3 py-2 text-[12px] font-medium transition ${
          isActive
            ? "bg-[linear-gradient(90deg,rgba(217,164,65,0.16),rgba(217,164,65,0.04))] text-white"
            : "text-[#cbbb9c] hover:bg-[#141c30] hover:text-white"
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            <span className="absolute -left-3 top-2 bottom-2 w-[3px] rounded-r-[3px] bg-[#d9a441]" />
          ) : null}

          <Icon
            name={item.icon}
            size={15}
          />

          <span>
            {item.label}
          </span>
        </>
      )}
    </NavLink>
  );
}

export function OrganizationShell({
  children,
  organizationName = "Current organization",
  organizationSlug,
}: OrganizationShellProps) {
  const location =
    useLocation();

  return (
    <div className="min-h-screen bg-[#f5efe3] text-[#191410] [font-family:Inter,system-ui,sans-serif]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[236px] flex-col border-r border-[#1e2a48] bg-[#080d18] text-[#cbbb9c] lg:flex">
        <div className="border-b border-[#1e2a48] bg-[linear-gradient(#1e2a48_1px,transparent_1px),linear-gradient(90deg,#1e2a48_1px,transparent_1px)] bg-[length:14px_14px] p-5">
          <div className="flex items-center gap-2.5">
            <BrandMark />

            <div className="min-w-0">
              <div className="font-[Archivo] text-[17px] font-semibold tracking-[-0.03em] text-white">
                Trace
              </div>

              <div className="mt-0.5 text-[8px] font-medium uppercase tracking-[0.2em] text-[#a2957c]">
                Construction Intelligence
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-5">
          <div className="mb-2 px-2 text-[9px] font-bold uppercase tracking-[0.18em] text-[#6b7891]">
            Workspace
          </div>

          <div className="space-y-1">
            {organizationNav.map(
              (item) => (
                <SidebarLink
                  key={item.to}
                  item={item}
                />
              ),
            )}
          </div>

          <div className="mb-2 mt-6 px-2 text-[9px] font-bold uppercase tracking-[0.18em] text-[#6b7891]">
            Project data
          </div>

          <div className="space-y-1">
            {productNav.map(
              (item) => (
                <SidebarLink
                  key={item.to}
                  item={item}
                />
              ),
            )}
          </div>
        </nav>

        <div className="border-t border-[#1e2a48] p-3">
          <div className="flex items-center gap-2.5 rounded-[10px] p-2 hover:bg-[#141c30]">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[linear-gradient(155deg,#4a5b82,#2a3652)] font-[Archivo] text-[11px] font-semibold text-white">
              OR
            </div>

            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] font-semibold text-white">
                {organizationName}
              </div>

              <div className="truncate text-[10px] text-[#a2957c]">
                {organizationSlug ??
                  "Organization workspace"}
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-[236px]">
        <header className="sticky top-0 z-30 flex min-h-[64px] items-center gap-3 border-b border-[#e1d5bc] bg-white/95 px-4 backdrop-blur sm:px-7">
          <div className="flex min-w-0 items-center gap-2 rounded-[8px] border border-[#e1d5bc] bg-[#fbf8f2] px-3 py-2">
            <Icon
              name="building"
              size={14}
            />

            <span className="max-w-[220px] truncate text-[12px] font-semibold text-[#332a21]">
              {organizationName}
            </span>
          </div>

          <div className="hidden h-9 max-w-[360px] flex-1 items-center gap-2 rounded-[8px] border border-[#e1d5bc] bg-[#fbf8f2] px-3 text-[#a2957c] md:flex">
            <Icon
              name="search"
              size={14}
            />

            <span className="text-[12px]">
              Search organization workspace
            </span>

            <span className="ml-auto rounded border border-[#e1d5bc] bg-white px-1.5 py-0.5 font-mono text-[9px]">
              ⌘K
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden items-center gap-2 text-[9px] font-bold uppercase tracking-[0.16em] text-[#668165] sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[#1e9d63]" />
              Workspace operational
            </div>

            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-[8px] border border-[#e1d5bc] bg-white text-[#6b6152] hover:bg-[#f5efe3]"
              aria-label="Current location"
              title={location.pathname}
            >
              <Icon
                name="settings"
                size={15}
              />
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