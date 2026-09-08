import type {PropsWithChildren, ReactNode,
} from "react";
import { Link } from "react-router-dom";

type AuthShellProps =
  PropsWithChildren<{
    eyebrow: string;
    title: ReactNode;
    description: string;
    footer?: ReactNode;
  }>;

export function AuthShell({
  eyebrow,
  title,
  description,
  footer,
  children,
}: AuthShellProps) {
  return (
    <main className="min-h-screen bg-[var(--color-workspace)] text-[var(--color-text-primary)]">
      <div className="grid min-h-screen lg:grid-cols-[0.92fr_1.08fr]">
        <aside className="relative hidden overflow-hidden bg-[var(--color-trace-navy-soft)] p-8 text-[var(--color-surface-muted)] lg:flex lg:flex-col lg:justify-between xl:p-10">
          <div
            className="
              absolute
              inset-0
              opacity-60
              [background-image:
                linear-gradient(rgba(255,255,255,.035)_1px,transparent_1px),
                linear-gradient(90deg,rgba(255,255,255,.035)_1px,transparent_1px)
              ]
              [background-size:28px_28px]
            "
          />

          <div className="relative">
            <Link
              to="/"
              className="inline-flex items-center gap-3"
            >
              <span className="grid h-10 w-10 place-items-center rounded-[10px] bg-[var(--color-trace-gold)] text-[var(--color-trace-navy)] shadow-[0_4px_14px_rgba(217,164,65,.28)]">
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M3 21h18" />
                  <path d="M5 21V8l7-5 7 5v13" />
                  <path d="M9 21v-6h6v6" />
                </svg>
              </span>

              <span>
                <span className="block font-['Archivo'] text-[17px] font-bold">
                  Trace
                </span>

                <span className="block text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                  Construction Intelligence
                </span>
              </span>
            </Link>
          </div>

          <div className="relative max-w-md">
            <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--color-trace-gold)]">
              One record of truth
            </p>

            <h2 className="font-['Fraunces'] text-4xl leading-[1.08] text-white xl:text-5xl">
              The work stays moving when the record stays clear.
            </h2>

            <p className="mt-4 max-w-sm text-[15px] leading-7 text-[var(--color-text-muted)]">
              Drawings, quantities, site progress,
              procurement and project intelligence
              connected in one workspace.
            </p>
          </div>

          <div className="relative flex items-center justify-between border-t border-white/10 pt-4">
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
              TRACE / IDENTITY
            </span>

            <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
              SECURE WORKSPACE
            </span>
          </div>
        </aside>

        <section className="flex min-h-screen items-center justify-center overflow-y-auto px-5 py-8 sm:px-8 lg:px-10 lg:py-6 xl:px-14">
          <div className="w-full max-w-[480px]">
            <div className="mb-6 lg:hidden">
              <Link to="/" className="inline-flex items-center gap-2.5">
                <span className="grid h-9 w-9 place-items-center rounded-[9px] bg-[var(--color-trace-navy)] text-[var(--color-trace-gold)]">
                  <span className="font-bold">
                    T
                  </span>
                </span>

                <span className="font-['Archivo'] text-[17px] font-bold">
                  Trace
                </span>
              </Link>
            </div>

            <div className="mb-6">
              <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-trace-gold-dark)]">
                {eyebrow}
              </p>

              <h1 className="font-['Fraunces'] text-[36px] leading-[1.05] tracking-[-0.02em] text-[var(--color-text-primary)] sm:text-[42px]">
                {title}
              </h1>

              <p className="mt-3 max-w-[430px] text-[15px] leading-6 text-[var(--color-text-secondary)]">
                {description}
              </p>
            </div>

            {children}

            {footer && <div className="mt-5">{footer}</div>}
          </div>
        </section>
      </div>
    </main>
  );
}