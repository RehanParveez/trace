import {
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
  useEffect, useRef, useState,
} from "react";
import type { OrganizationIconName } from "../types/organization.types";

const iconPaths: Record<OrganizationIconName, ReactNode> = {
  building: (
    <>
      <path d="M3 21h18" />
      <path d="M6 21V9l6-6 6 6v12" />
      <path d="M10 21v-5h4v5" />
      <path d="M10 11h.01M14 11h.01M10 8h.01M14 8h.01" />
    </>
  ),
  settings: (
    <>
      <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" />
      <path d="m19 13.2 1.2.9-1.8 3.1-1.4-.6a7.8 7.8 0 0 1-1.6.9l-.2 1.5h-3.6l-.2-1.5a7.8 7.8 0 0 1-1.6-.9l-1.4.6-1.8-3.1 1.2-.9a7.7 7.7 0 0 1 0-1.9l-1.2-.9 1.8-3.1 1.4.6a7.8 7.8 0 0 1 1.6-.9l.2-1.5h3.6l.2 1.5a7.8 7.8 0 0 1 1.6.9l1.4-.6 1.8 3.1-1.2.9a7.7 7.7 0 0 1 0 1.9Z" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0" />
      <path d="M16 5a3 3 0 1 1 0 6M16 14a5 5 0 0 1 5 5" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 20 6v5c0 5-3.2 8.3-8 10-4.8-1.7-8-5-8-10V6l8-3Z" />
      <path d="m8.5 12 2.2 2.2 4.8-5" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m4 7 8 6 8-6" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 1.4 5.6L19 10l-5.6 1.4L12 17l-1.4-5.6L5 10l5.6-1.4L12 3Z" />
      <path d="m19 15 .6 2.4L22 18l-2.4.6L19 21l-.6-2.4L16 18l2.4-.6L19 15Z" />
    </>
  ),
  check: <path d="m5 12 4 4L19 7" />,
  x: <path d="m7 7 10 10M17 7 7 17" />,
  arrow: (
    <>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </>
  ),
  chevron: <path d="m9 18 6-6-6-6" />,
  edit: (
    <>
      <path d="m4 20 4.2-1 9.7-9.7a2.2 2.2 0 0 0-3.1-3.1L5.1 15.9 4 20Z" />
      <path d="m13.5 7.5 3 3" />
    </>
  ),
  plus: (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="3" />
      <path d="M5 21a7 7 0 0 1 14 0" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="10" width="14" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
  logout: (
    <>
      <path d="M10 5H5v14h5" />
      <path d="M13 8l4 4-4 4M17 12H9" />
    </>
  ),
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="8" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  projects: <path d="M3 21h18M6 21V9l6-4 6 4v12M10 21v-5h4v5" />,
  budget: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <path d="M8 9h8M8 13h5" />
    </>
  ),
  site: <path d="M4 19V5h16v14M4 9h16M8 5v14M16 5v14" />,
  procurement: <path d="M4 7h16M6 7v12h12V7M9 7V4h6v3" />,
  expenses: (
    <>
      <path d="M5 4h14v16H5z" />
      <path d="M8 8h8M8 12h5M8 16h3" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 11a8 8 0 0 0-14.7-4L3 10" />
      <path d="M3 5v5h5M4 13a8 8 0 0 0 14.7 4L21 14" />
      <path d="M21 19v-5h-5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </>
  ),
  key: (
    <>
      <circle cx="8" cy="14.5" r="4" />
      <path d="m11 11.5 9-9M17 5.5l2.5 2.5M14 8.5 16 10.5" />
    </>
  ),
  filter: <path d="M4 5h16l-6.5 7.5V19l-3 2v-8.5L4 5Z" />,
  trend: (
    <>
      <path d="m3 17 6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </>
  ),
  download: (
    <>
      <path d="M12 4v11m0 0 4-4m-4 4-4-4" />
      <path d="M4 18v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3 2 20h20L12 3Z" />
      <path d="M12 10v4M12 17h.01" />
    </>
  ),
  dot: <circle cx="12" cy="12" r="4" />,
  copy: (
    <>
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </>
  ),
  external: (
    <>
      <path d="M14 4h6v6" />
      <path d="M20 4 10 14" />
      <path d="M19 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5" />
    </>
  ),
};

export function Icon({
  name,
  size = 16,
  strokeWidth = 1.8,
  className = "",
}: {
  name: OrganizationIconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {iconPaths[name]}
    </svg>
  );
}

export function BrandMark() {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[linear-gradient(155deg,#d9a441,#b98626)] text-[13px] font-extrabold text-[#080d18] shadow-[0_2px_8px_rgba(217,164,65,0.35)]">
      T
    </div>
  );
}

export function Panel({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={`rounded-[16px] border border-[#e1d5bc] bg-[#fbf8f2] shadow-[0_1px_2px_rgba(90,70,40,0.04)] ${className}`}
      {...props}
    >
      {children}
    </section>
  );
}

export function PanelHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[#e1d5bc] px-5 py-4">
      <div className="min-w-0">
        {eyebrow ? (
          <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-[#a2957c]">
            {eyebrow}
          </div>
        ) : null}

        <h2 className="font-[Archivo] text-[15px] font-bold tracking-[-0.02em] text-[#191410]">
          {title}
        </h2>

        {description ? (
          <p className="mt-1 max-w-2xl text-[12px] leading-5 text-[#6b6152]">
            {description}
          </p>
        ) : null}
      </div>

      {action}
    </div>
  );
}

export function SectionDivider({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 mt-8 flex flex-wrap items-baseline justify-between gap-4 first:mt-0">
      <div>
        <h2 className="font-['Fraunces',serif] text-[20px] font-semibold italic tracking-[-0.01em] text-[#191410]">
          {title}
        </h2>

        {description ? (
          <p className="mt-1 text-[12.5px] text-[#6b6152]">{description}</p>
        ) : null}
      </div>

      {action}
    </div>
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
}) {
  const variants = {
    primary:
      "border-[#d9a441] bg-[#d9a441] text-[#080d18] hover:bg-[#b98626]",
    secondary: "border-[#e1d5bc] bg-white text-[#332a21] hover:bg-[#f5efe3]",
    ghost: "border-transparent bg-transparent text-[#6b6152] hover:bg-[#efe6d3]",
    danger: "border-[#efc5bd] bg-[#fff7f5] text-[#a33f31] hover:bg-[#f9e5df]",
  };

  const sizes = {
    sm: "min-h-8 px-3 text-[12px]",
    md: "min-h-9 px-3.5 text-[13px]",
  };

  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-[8px] border font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({
  tone = "slate",
  children,
}: {
  tone?: "green" | "red" | "blue" | "gold" | "slate";
  children: ReactNode;
}) {
  const tones = {
    green: "bg-[#e4f5ec] text-[#1e9d63]",
    red: "bg-[#f9e5df] text-[#c24a3a]",
    blue: "bg-[#e7f0fa] text-[#3b7dc4]",
    gold: "bg-[#fbefd9] text-[#b98626]",
    slate: "bg-[#efe6d3] text-[#6b6152]",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10.5px] font-semibold ${tones[tone]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function LivePip({
  label = "Live",
  tone = "green",
}: {
  label?: string;
  tone?: "green" | "gold";
}) {
  const dot = tone === "green" ? "bg-[#3ddc8a]" : "bg-[#d9a441]";
  const text = tone === "green" ? "text-[#7fd9a8]" : "text-[#d9a441]";

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.08em] ${text}`}
    >
      <span className={`relative flex h-1.5 w-1.5 ${dot} rounded-full`}>
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full ${dot} opacity-60`}
        />
      </span>
      {label}
    </span>
  );
}

export function GlassChip({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: OrganizationIconName;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2.5 rounded-[12px] border border-white/[0.14] bg-[#0a0f19]/50 px-3.5 py-2.5 text-white backdrop-blur-[6px]">
      {icon ? (
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-white/10 text-[#d9a441]">
          <Icon name={icon} size={14} />
        </span>
      ) : null}

      <span className="min-w-0">
        <span className="block text-[10px] leading-none text-white/60">
          {label}
        </span>

        <span className="mt-1 block truncate font-[Archivo] text-[13px] font-bold leading-none">
          {value}
        </span>
      </span>
    </div>
  );
}

export function Avatar({
  initials,
  size = "md",
}: {
  initials: string;
  size?: "sm" | "md" | "lg";
}) {
  const sizes = {
    sm: "h-7 w-7 text-[9px]",
    md: "h-9 w-9 text-[11px]",
    lg: "h-12 w-12 text-[14px]",
  };

  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full bg-[linear-gradient(155deg,#4a5b82,#2a3652)] font-[Archivo] font-semibold text-white ${sizes[size]}`}
    >
      {initials}
    </div>
  );
}

export function StatCard({
  label,
  value,
  note,
  icon,
  tone = "gold",
}: {
  label: string;
  value: string | number;
  note?: string;
  icon: OrganizationIconName;
  tone?: "gold" | "green" | "blue" | "red";
}) {
  const iconTone = {
    gold: "bg-[#fbefd9] text-[#b98626]",
    green: "bg-[#e4f5ec] text-[#1e9d63]",
    blue: "bg-[#e7f0fa] text-[#3b7dc4]",
    red: "bg-[#f9e5df] text-[#c24a3a]",
  }[tone];

  return (
    <Panel className="relative overflow-hidden p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10.5px] font-bold uppercase tracking-[0.06em] text-[#a2957c]">
            {label}
          </div>

          <div className="mt-1.5 font-mono text-[25px] font-semibold tracking-[-0.04em] text-[#191410]">
            {value}
          </div>

          {note ? (
            <div className="mt-1 text-[11px] text-[#6b6152]">{note}</div>
          ) : null}
        </div>

        <div
          className={`flex h-8 w-8 items-center justify-center rounded-[9px] ${iconTone}`}
        >
          <Icon name={icon} size={15} />
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-[linear-gradient(180deg,transparent,rgba(217,164,65,0.06))]" />
    </Panel>
  );
}

export function PageHeader({
  eyebrow = "ORGANIZATION CONTROL",
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="mb-2 flex items-center gap-2.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[#a2957c]">
          <span className="h-px w-7 bg-[#d9a441]" />
          {eyebrow}
        </div>

        <h1 className="font-[Archivo] text-[26px] font-bold leading-tight tracking-[-0.04em] text-[#191410] sm:text-[30px]">
          {title}
        </h1>

        <p className="mt-1.5 max-w-2xl text-[13px] leading-5 text-[#6b6152]">
          {description}
        </p>
      </div>

      {actions ? (
        <div className="flex items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-[0.04em] text-[#6b6152]">
        {label}
      </span>

      {children}

      {error ? (
        <span className="mt-1.5 block text-[11px] text-[#c24a3a]">
          {error}
        </span>
      ) : hint ? (
        <span className="mt-1.5 block text-[11px] leading-4 text-[#a2957c]">
          {hint}
        </span>
      ) : null}
    </label>
  );
}

export const inputClass =
  "w-full rounded-[8px] border border-[#e1d5bc] bg-white px-3 py-2 text-[13px] text-[#191410] outline-none transition focus:border-[#b98626] focus:ring-2 focus:ring-[#d9a441]/15 disabled:bg-[#f5efe3] disabled:text-[#a2957c]";

export function ProgressBar({
  value,
  tone = "gold",
  size = "md",
}: {
  value: number;
  tone?: "gold" | "green" | "blue" | "red";
  size?: "sm" | "md";
}) {
  const fills = {
    gold: "bg-[linear-gradient(90deg,#b98626,#d9a441)]",
    green: "bg-[linear-gradient(90deg,#17805a,#1e9d63)]",
    blue: "bg-[linear-gradient(90deg,#2f68a8,#3b7dc4)]",
    red: "bg-[linear-gradient(90deg,#b93a32,#c24a3a)]",
  };

  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div
      className={`w-full overflow-hidden rounded-full bg-[#efe6d3] ${size === "sm" ? "h-1.5" : "h-[7px]"}`}
    >
      <div
        className={`h-full rounded-full transition-[width] ${fills[tone]}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  disabled = false,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        checked
          ? "border-[#b98626] bg-[#d9a441]"
          : "border-[#e1d5bc] bg-[#e1d5bc]"
      }`}
    >
      <span
        className={`inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow-sm transition-transform ${
          checked ? "translate-x-[22px]" : "translate-x-[3px]"
        }`}
      />
    </button>
  );
}

export interface MenuAction {
  label: string;
  icon?: OrganizationIconName;
  onSelect: () => void;
  tone?: "default" | "danger";
  disabled?: boolean;
}

export function DropdownMenu({
  items,
  align = "end",
}: {
  items: MenuAction[];
  align?: "start" | "end";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);

    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative inline-block text-left">
      <button
        type="button"
        aria-label="More actions"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex h-8 w-8 items-center justify-center rounded-[8px] text-[#6b6152] transition hover:bg-[#efe6d3]"
      >
        <Icon name="more" size={15} />
      </button>

      {open ? (
        <div
          role="menu"
          className={`absolute top-[calc(100%+4px)] z-30 min-w-[180px] overflow-hidden rounded-[10px] border border-[#e1d5bc] bg-white py-1 shadow-[0_16px_40px_rgba(8,13,24,0.14)] ${
            align === "end" ? "right-0" : "left-0"
          }`}
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
              className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-[12.5px] font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${
                item.tone === "danger"
                  ? "text-[#c24a3a] hover:bg-[#f9e5df]"
                  : "text-[#332a21] hover:bg-[#f5efe3]"
              }`}
            >
              {item.icon ? <Icon name={item.icon} size={13} /> : null}
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function Modal({
  title,
  description,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#080d18]/70 p-4 backdrop-blur-[2px]">
      <div
        className={`w-full overflow-hidden rounded-[16px] border border-[#e1d5bc] bg-[#fbf8f2] shadow-[0_24px_70px_rgba(8,13,24,0.35)] ${
          wide ? "max-w-2xl" : "max-w-md"
        }`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-[#e1d5bc] px-5 py-4">
          <div>
            <h2 className="font-[Archivo] text-[16px] font-bold text-[#191410]">
              {title}
            </h2>

            {description ? (
              <p className="mt-1 text-[12px] leading-5 text-[#6b6152]">
                {description}
              </p>
            ) : null}
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="flex h-8 w-8 items-center justify-center rounded-[8px] text-[#6b6152] hover:bg-[#efe6d3]"
          >
            <Icon name="x" size={16} />
          </button>
        </div>

        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function EmptyState({
  icon = "info",
  title,
  description,
  action,
}: {
  icon?: OrganizationIconName;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-[10px] bg-[#efe6d3] text-[#6b6152]">
        <Icon name={icon} size={18} />
      </div>

      <h3 className="font-[Archivo] text-[14px] font-bold text-[#191410]">
        {title}
      </h3>

      <p className="mt-1 max-w-md text-[12px] leading-5 text-[#6b6152]">
        {description}
      </p>

      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function LoadingState({
  label = "Loading workspace…",
}: {
  label?: string;
}) {
  return (
    <div className="flex min-h-[280px] items-center justify-center rounded-[16px] border border-[#e1d5bc] bg-[#fbf8f2]">
      <div className="flex items-center gap-3 text-[12px] font-medium text-[#6b6152]">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#e1d5bc] border-t-[#d9a441]" />
        {label}
      </div>
    </div>
  );
}

export function ErrorState({
  title = "We couldn't load this workspace",
  description = "The request failed. Check your connection and try again.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-[16px] border border-[#efc5bd] bg-[#fff7f5] p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[9px] bg-[#f9e5df] text-[#c24a3a]">
          <Icon name="alert" size={15} />
        </div>

        <div>
          <h2 className="font-[Archivo] text-[14px] font-bold text-[#191410]">
            {title}
          </h2>

          <p className="mt-1 text-[12px] leading-5 text-[#6b6152]">
            {description}
          </p>

          {onRetry ? (
            <Button className="mt-3" size="sm" onClick={onRetry}>
              <Icon name="refresh" size={13} />
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function TableShell({ children }: { children: ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#a2957c]">
      {children}
    </div>
  );
}

export function Divider() {
  return <div className="h-px bg-[#e1d5bc]" />;
}
