import { NavLink } from "react-router-dom";
import { Icon } from "./OrganizationUi";
import type { OrganizationIconName } from "../types/organization.types";

export interface NavItem {
  label: string;
  to: string;
  icon: OrganizationIconName;
  exact?: boolean;
  badge?: number;
}

export function SidebarLink({ item }: { item: NavItem }) {
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

export interface SearchDestination {
  label: string;
  to: string;
  icon: OrganizationIconName;
  group: string;
}

export const NAV_SEARCH_DESTINATIONS: SearchDestination[] = [
  { label: "Overview", to: "/app/organization", icon: "dashboard", group: "Workspace" },
  { label: "Settings", to: "/app/organization/settings", icon: "settings", group: "Organization" },
  { label: "Members", to: "/app/organization/members", icon: "users", group: "Organization" },
  { label: "Roles & access", to: "/app/organization/roles", icon: "shield", group: "Organization" },
  { label: "Invitations", to: "/app/organization/invitations", icon: "mail", group: "Organization" },
  { label: "Subscription", to: "/app/subscription", icon: "budget", group: "Organization" },
  { label: "Material library", to: "/app/drawings_boq", icon: "materials", group: "Organization" },
  { label: "Labour rates", to: "/app/drawings_boq/labour-rates", icon: "budget", group: "Organization" },
  { label: "WhatsApp connection", to: "/app/whatsapp-settings", icon: "external", group: "Organization" },
  { label: "Projects", to: "/app/projects", icon: "projects", group: "Projects" },
  { label: "Budgets", to: "/app/budgets", icon: "budget", group: "Projects" },
  { label: "Progress review", to: "/app/progress-review", icon: "check", group: "Projects" },
  { label: "Site photos", to: "/app/site-photos", icon: "spark", group: "Projects" },
  { label: "Site progress", to: "/app/site-logs", icon: "site", group: "Projects" },
  { label: "Procurement", to: "/app/procurement", icon: "procurement", group: "Projects" },
  { label: "Expenses", to: "/app/expenses", icon: "expenses", group: "Projects" },
  { label: "AI activity", to: "/app/ai-activity", icon: "spark", group: "Intelligence" },
  { label: "Audit log", to: "/app/audit-log", icon: "shield", group: "Intelligence" },
];