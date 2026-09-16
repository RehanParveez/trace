import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Icon, inputClass } from "../../organizations/components/OrganizationUi";
import type { Project } from "../types/project.types";

interface ProjectComboboxProps {
  projects: Project[];
  value: string;
  onChange: (projectId: string) => void;
  placeholder?: string;
}

export function ProjectCombobox({
  projects,
  value,
  onChange,
  placeholder = "Search projects…",
}: ProjectComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const selectedProject = projects.find((project) => project.id === value);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return projects;
    return projects.filter((project) => project.name.toLowerCase().includes(term));
  }, [projects, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;

    function handleClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  useEffect(() => {
    if (open) {
      optionRefs.current[activeIndex]?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex, open]);

  function selectProject(projectId: string) {
    onChange(projectId);
    setOpen(false);
    inputRef.current?.blur();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open && (event.key === "ArrowDown" || event.key === "Enter")) {
      setOpen(true);
      return;
    }

    if (!open) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const project = filtered[activeIndex];
      if (project) {
        selectProject(project.id);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          className={`${inputClass} pl-9`}
          value={open ? query : selectedProject?.name ?? ""}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(0);
            if (!open) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
        />
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]">
          <Icon name="search" size={14} />
        </span>
      </div>

      {open ? (
        <div
          role="listbox"
          className="absolute z-20 mt-1.5 max-h-64 w-full overflow-y-auto rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] py-1 shadow-[0_16px_40px_rgba(8,13,24,0.14)]"
        >
          {filtered.length === 0 ? (
            <div className="px-3.5 py-2.5 text-[13px] text-[var(--color-text-muted)]">
              No projects match "{query}"
            </div>
          ) : (
            filtered.map((project, index) => (
              <button
                key={project.id}
                ref={(element) => {
                  optionRefs.current[index] = element;
                }}
                type="button"
                role="option"
                aria-selected={project.id === value}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => selectProject(project.id)}
                className={`flex w-full items-center gap-2 px-3.5 py-2.5 text-left text-[13.5px] transition ${
                  index === activeIndex
                    ? "bg-[var(--color-surface-muted)] text-[var(--color-text-primary)]"
                    : "text-[var(--color-text-primary)] hover:bg-[var(--color-surface-muted)]"
                }`}
              >
                {project.id === value ? (
                  <Icon name="check" size={13} className="text-[var(--color-trace-gold-dark)]" />
                ) : (
                  <span className="w-[13px]" />
                )}
                <span className="truncate">{project.name}</span>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}