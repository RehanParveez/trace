import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { BrandMark, Icon, LivePip } from "./OrganizationUi";
import { SidebarLink } from "./SidebarNav";
import type { NavItem } from "./SidebarNav";

interface MobileNavDrawerProps {
  open: boolean;
  onClose: () => void;
  organizationName: string;
  organizationSlug?: string;
  navGroups: { label: string; items: NavItem[] }[];
}

export function MobileNavDrawer({
  open,
  onClose,
  organizationName,
  organizationSlug,
  navGroups,
}: MobileNavDrawerProps) {
  const location = useLocation();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    onClose();

  }, [location.pathname]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || !panelRef.current) {
        return;
      }

      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );

      if (focusable.length === 0) {
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[95] lg:hidden">
      <div
        className="absolute inset-0 bg-[var(--color-trace-navy)]/60 backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        className="absolute inset-y-0 left-0 flex w-[280px] max-w-[82vw] flex-col overflow-hidden !border-r !border-[#24314d] !bg-[var(--color-trace-navy)] !text-[#cbd5e1] shadow-[0_0_60px_rgba(0,0,0,0.4)]"
      >
        <div className="relative flex h-[72px] shrink-0 items-center justify-between !border-b !border-[#24314d] px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <BrandMark />
            <div className="min-w-0">
              <div className="truncate font-[Archivo] text-[16px] font-semibold tracking-[-0.03em] !text-white">
                Trace
              </div>
              <div className="truncate text-[8px] font-semibold uppercase tracking-[0.16em] !text-[#8795aa]">
                Construction Intelligence
              </div>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] !text-[#9eacc1] outline-none transition hover:!bg-[#121c30] focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)]"
          >
            <Icon name="x" size={18} />
          </button>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-5">
          {navGroups.map((group) => (
            <div key={group.label} className="mb-6 last:mb-0">
              <div className="mb-3 px-2 text-[9px] font-bold uppercase tracking-[0.18em] !text-[#78869c]">
                {group.label}
              </div>

              <div className="space-y-1">
                {group.items.map((item) => (
                  <SidebarLink key={item.to} item={item} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="shrink-0 !border-t !border-[#24314d] p-4">
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
      </div>
    </div>
  );
}