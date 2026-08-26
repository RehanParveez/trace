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
    <main className="min-h-screen bg-[#F5EFE3] text-[#191410]">
      <div className="grid min-h-screen lg:grid-cols-[0.92fr_1.08fr]">
        <aside
          className="
            relative
            hidden
            overflow-hidden
            bg-[#0D1424]
            p-8
            text-[#FBF8F2]
            lg:flex
            lg:flex-col
            lg:justify-between
            xl:p-10
          "
        >
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
              <span
                className="
                  grid
                  h-10
                  w-10
                  place-items-center
                  rounded-[10px]
                  bg-[#D9A441]
                  text-[#080D18]
                  shadow-[0_4px_14px_rgba(217,164,65,.28)]
                "
              >
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

                <span className="block text-[10px] uppercase tracking-[.08em] text-[#A2957C]">
                  Construction Intelligence
                </span>
              </span>
            </Link>
          </div>

          <div className="relative max-w-md">
            <p className="mb-4 font-mono text-[10px] uppercase tracking-[.14em] text-[#D9A441]">
              One record of truth
            </p>

            <h2 className="font-['Fraunces'] text-4xl leading-[1.08] text-[#FBF8F2] xl:text-5xl">
              The work stays moving when the record stays clear.
            </h2>

            <p className="mt-4 max-w-sm text-sm leading-7 text-[#A2957C]">
              Drawings, quantities, site progress,
              procurement and project intelligence
              connected in one workspace.
            </p>
          </div>

          <div className="relative flex items-center justify-between border-t border-white/10 pt-4">
            <span className="font-mono text-[9px] uppercase tracking-[.12em] text-[#706A62]">
              TRACE / IDENTITY
            </span>

            <span className="font-mono text-[9px] text-[#706A62]">
              SECURE WORKSPACE
            </span>
          </div>
        </aside>

        <section
          className="
            flex
            min-h-screen
            items-center
            justify-center
            overflow-y-auto
            px-5
            py-5
            sm:px-8
            lg:px-10
            lg:py-4
            xl:px-14
          "
        >
          <div className="w-full max-w-[480px]">
            <div className="mb-6 lg:hidden">
              <Link
                to="/"
                className="inline-flex items-center gap-2"
              >
                <span className="grid h-9 w-9 place-items-center rounded-[9px] bg-[#0D1424] text-[#D9A441]">
                  <span className="font-bold">
                    T
                  </span>
                </span>

                <span className="font-['Archivo'] text-[17px] font-bold">
                  Trace
                </span>
              </Link>
            </div>

            <div className="mb-4">
              <p className="mb-1.5 font-mono text-[10px] font-semibold uppercase tracking-[.14em] text-[#B98626]">
                {eyebrow}
              </p>

              <h1 className="font-['Fraunces'] text-[34px] leading-[1.02] tracking-[-.02em] text-[#191410] sm:text-[40px]">
                {title}
              </h1>

              <p className="mt-2 max-w-[430px] text-[13px] leading-5 text-[#776D5E]">
                {description}
              </p>
            </div>

            {children}

            {footer && (
              <div className="mt-4">
                {footer}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}