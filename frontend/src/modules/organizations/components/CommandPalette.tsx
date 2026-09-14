import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "./OrganizationUi";
import { NAV_SEARCH_DESTINATIONS } from "./SidebarNav";
import type { OrganizationIconName } from "../types/organization.types";
import { useProjects } from "../../projects";

interface CommandPaletteProps {
  onClose: () => void;
}

interface ResultItem {
  key: string;
  label: string;
  sublabel?: string;
  to: string;
  icon: OrganizationIconName;
}

export function CommandPalette({ onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const projectsQuery = useProjects();

  useEffect(() => {
    inputRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const results = useMemo<ResultItem[]>(() => {
    const normalized = query.trim().toLowerCase();

    const navResults: ResultItem[] = NAV_SEARCH_DESTINATIONS
      .filter((item) => !normalized || item.label.toLowerCase().includes(normalized))
      .map((item) => ({
        key: `nav:${item.to}`,
        label: item.label,
        sublabel: item.group,
        to: item.to,
        icon: item.icon,
      }));

    const projectResults: ResultItem[] = normalized
      ? (projectsQuery.data ?? [])
          .filter((project) => project.name.toLowerCase().includes(normalized))
          .slice(0, 8)
          .map((project) => ({
            key: `project:${project.id}`,
            label: project.name,
            sublabel: "Project",
            to: `/app/projects/${project.id}`,
            icon: "projects" as const,
          }))
      : [];

    return [...projectResults, ...navResults].slice(0, 20);
  }, [query, projectsQuery.data]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  function goTo(result: ResultItem) {
    navigate(result.to);
    onClose();
  }

  function handleInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const selected = results[activeIndex];
      if (selected) {
        goTo(selected);
      }
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center bg-[var(--color-trace-navy)]/60 px-4 pt-[12vh] backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-lg overflow-hidden rounded-[var(--radius-xl)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[0_24px_70px_rgba(8,13,24,0.35)]"
      >
        <div className="flex items-center gap-2.5 border-b border-[var(--color-border)] px-4 py-3.5">
          <Icon name="search" size={16} className="shrink-0 text-[var(--color-text-muted)]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Search pages or projects…"
            aria-label="Search pages or projects"
            className="w-full bg-transparent text-[14px] text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)]"
          />
          <kbd className="shrink-0 rounded border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text-muted)]">
            Esc
          </kbd>
        </div>

        <div className="max-h-[360px] overflow-y-auto p-2">
          {results.length === 0 ? (
            <div className="px-3 py-8 text-center text-[13px] text-[var(--color-text-secondary)]">
              Nothing matches "{query}"
            </div>
          ) : (
            results.map((result, index) => (
              <button
                key={result.key}
                type="button"
                onClick={() => goTo(result)}
                onMouseEnter={() => setActiveIndex(index)}
                className={`flex w-full items-center gap-3 rounded-[8px] px-3 py-2.5 text-left transition ${
                  index === activeIndex ? "bg-[var(--color-warning-bg)]" : "hover:bg-[var(--color-surface-muted)]"
                }`}
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]">
                  <Icon name={result.icon} size={14} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13.5px] font-medium text-[var(--color-text-primary)]">
                    {result.label}
                  </span>
                  {result.sublabel ? (
                    <span className="block text-[11px] text-[var(--color-text-muted)]">{result.sublabel}</span>
                  ) : null}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}