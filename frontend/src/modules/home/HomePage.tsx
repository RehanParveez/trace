import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import "../home/landing.css";

function Icon({
  name,
}: {
  name:
    | "flow"
    | "budget"
    | "site"
    | "materials"
    | "lock"
    | "arrow"
    | "chart"
    | "team";
}) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  const paths: Record<string, ReactNode> = {
    flow: (
      <>
        <path d="M4 6h6v5H4zM14 13h6v5h-6z" />
        <path d="M10 8.5h4M17 13V8.5H10" />
      </>
    ),

    budget: (
      <>
        <path d="M4 19V9m5 10V5m5 14v-7m5 7V3" />
        <path d="M3 19h18" />
      </>
    ),

    site: (
      <>
        <path d="M4 19V5h16v14" />
        <path d="M7 9h10M7 13h6M7 17h8" />
      </>
    ),

    materials: (
      <>
        <path d="m4 8 8-4 8 4-8 4-8-4Z" />
        <path d="M4 12l8 4 8-4M4 16l8 4 8-4" />
      </>
    ),

    lock: (
      <>
        <rect x="5" y="10" width="14" height="10" rx="2" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      </>
    ),

    arrow: (
      <>
        <path d="M5 12h13M13 7l5 5-5 5" />
      </>
    ),

    chart: (
      <>
        <path d="M4 19V5M4 19h17" />
        <path d="m7 15 4-4 3 2 5-6" />
      </>
    ),

    team: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 20a6 6 0 0 1 12 0M16 11a3 3 0 1 0 0-6M16 14a5 5 0 0 1 5 5" />
      </>
    ),
  };

  return <svg {...common}>{paths[name]}</svg>;
}

const capabilities = [
  [
    "budget",
    "Budget control",
    "Connect approved budgets to actual project activity without turning the frontend into an accounting engine.",
  ],
  [
    "site",
    "Site progress",
    "Capture daily progress, blockers, workforce and delivery context from the field.",
  ],
  [
    "materials",
    "Materials & procurement",
    "Move from material request to purchase order to goods receipt with one operational trail.",
  ],
  [
    "chart",
    "Project cost visibility",
    "Bring progress, commitments, receipts and approved expenses into one project picture.",
  ],
] as const;

const roles = [
  [
    "team",
    "Company leadership",
    "See where projects stand and where cost, progress or procurement needs attention.",
  ],
  [
    "site",
    "Site teams",
    "Record the work happening on site while the details are still fresh.",
  ],
  [
    "materials",
    "Procurement & stores",
    "Keep requests, orders and received materials connected.",
  ],
  [
    "budget",
    "Finance & control",
    "Follow approved budgets, commitments and actual project cost.",
  ],
] as const;

function DashboardMockup() {
  return (
    <div className="lp-dashboard">
      <div className="lp-dash-top">
        <div className="lp-dash-brand">
          <span className="lp-mini-mark">T</span>
          <span>Trace</span>
        </div>

        <span className="lp-dash-user">
          Company Admin · EN
        </span>
      </div>

      <div className="lp-dash-body">
        <aside className="lp-dash-side">
          <span className="active">Overview</span>
          <span>Projects</span>
          <span>Budgets</span>
          <span>Site reports</span>
          <span>Procurement</span>
          <span>Expenses</span>
        </aside>

        <div className="lp-dash-main">
          <div className="lp-dash-heading">
            <div>
              <small>PROJECT CONTROL</small>
              <strong>Good morning, Trace</strong>
            </div>

            <span className="lp-demo-pill">
              LIVE WORKSPACE
            </span>
          </div>

          <div className="lp-kpis">
            <div>
              <small>ACTIVE PROJECTS</small>
              <b>08</b>
              <em>+2 this month</em>
            </div>

            <div>
              <small>APPROVED BUDGET</small>
              <b>Rs 84.6M</b>
              <em>91% allocated</em>
            </div>

            <div>
              <small>PROJECT PROGRESS</small>
              <b>67%</b>
              <em>+4.8% this month</em>
            </div>
          </div>

          <div className="lp-dash-grid">
            <div className="lp-chart-card">
              <div className="lp-card-head">
                <b>Project cost & progress</b>
                <span>Last 6 months</span>
              </div>

              <div className="lp-chart">
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
                <div className="lp-chart-line" />
              </div>
            </div>

            <div className="lp-project-card">
              <div className="lp-card-head">
                <b>Projects needing attention</b>
                <span>View all</span>
              </div>

              <div className="lp-project-row">
                <span>Highland Business Park</span>
                <b>72%</b>
                <small>Budget watch</small>
              </div>

              <div className="lp-project-row">
                <span>Riverside Mall</span>
                <b>41%</b>
                <small>2 pending receipts</small>
              </div>

              <div className="lp-project-row">
                <span>North Avenue Villas</span>
                <b>88%</b>
                <small>On track</small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function HomePage() {
  return (
    <main className="lp-page">
      <nav className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <Link to="/" className="lp-logo">
            <span className="lp-logo-mark">T</span>
            <span>Trace</span>
          </Link>

          <div className="lp-nav-links">
            <a href="#product">Product</a>
            <a href="#workflow">Workflow</a>
            <a href="#teams">Teams</a>
            <a href="#principles">Why Trace</a>
          </div>

          <div className="lp-nav-actions">
            <span className="lp-live">
              <i />
              Operational workspace
            </span>

            <Link
              to="/login"
              className="lp-btn lp-btn-ghost"
            >
              Sign in
            </Link>

            <Link
              to="/register"
              className="lp-btn lp-btn-primary"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      <section className="lp-hero">
        <div className="lp-wrap lp-hero-grid">
          <div className="lp-hero-copy">
            <p className="lp-eyebrow">
              CONSTRUCTION INTELLIGENCE · ONE RECORD OF TRUTH
            </p>

            <h1>
              Keep the work moving when the{" "}
              <em>record stays clear.</em>
            </h1>

            <p className="lp-hero-sub">
              Trace connects budgets, physical progress, materials,
              procurement, deliveries and expenses into one operational
              picture for construction teams.
            </p>

            <div className="lp-actions">
              <Link
                to="/register"
                className="lp-btn lp-btn-primary lp-btn-large"
              >
                Build with Trace
                <Icon name="arrow" />
              </Link>

              <a
                href="#product"
                className="lp-btn lp-btn-ghost lp-btn-large"
              >
                See how it works
              </a>
            </div>

            <div className="lp-proof">
              <span>
                <Icon name="lock" />
                Permission-aware
              </span>

              <span>
                <Icon name="flow" />
                Workflow-first
              </span>

              <span>
                <Icon name="chart" />
                Backend-authoritative
              </span>
            </div>
          </div>

          <div className="lp-hero-stage">
            <div className="lp-hero-canvas">
              <div className="lp-grid-bg" />

              <div className="lp-shot lp-shot-back">
                <DashboardMockup />
              </div>

              <div className="lp-shot lp-shot-front">
                <DashboardMockup />
              </div>

              <div className="lp-glass lp-glass-one">
                <b>67%</b>
                <span>project progress</span>
              </div>

              <div className="lp-glass lp-glass-two">
                <b>Rs 84.6M</b>
                <span>approved budget</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="lp-stat" id="principles">
        <div className="lp-wrap">
          <div className="lp-stat-num">
            One connected operational chain.
          </div>

          <p>
            From approved BOQ and budget to site progress, procurement,
            delivery, expenses and project-cost visibility.
          </p>

          <div className="lp-tags">
            <span>
              <Icon name="budget" />
              Budget
            </span>

            <span>
              <Icon name="site" />
              Progress
            </span>

            <span>
              <Icon name="materials" />
              Procurement
            </span>

            <span>
              <Icon name="materials" />
              Receipts
            </span>

            <span>
              <Icon name="chart" />
              Cost
            </span>
          </div>

          <div className="lp-origin">
            <b>T</b>

            <p>
              Trace is designed around the real construction workflow rather
              than a collection of disconnected CRUD screens. The system
              keeps the backend authoritative, permissions explicit and
              important operational changes traceable.
            </p>
          </div>
        </div>
      </section>

      <section className="lp-section" id="product">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              THE PRODUCT
            </p>

            <h2>
              See the whole project, without losing the details that make it
              real.
            </h2>
          </div>

          <div className="lp-tour">
            <div className="lp-tour-main">
              <DashboardMockup />

              <div className="lp-tour-cap">
                <b>Project control dashboard</b>
                <span>
                  Progress · budget · commitments · attention points
                </span>
              </div>
            </div>

            <div className="lp-tour-small">
              <div className="lp-mini-panel">
                <small>APPROVED BUDGET</small>
                <strong>Rs 42.8M</strong>

                <div className="lp-meter">
                  <i style={{ width: "68%" }} />
                </div>

                <span>68% committed</span>
              </div>

              <div className="lp-tour-cap">
                <b>Financial control</b>
                <span>
                  Backend-calculated project values
                </span>
              </div>
            </div>

            <div className="lp-tour-small">
              <div className="lp-mini-panel">
                <small>MATERIAL REQUEST</small>
                <strong>MR-0248</strong>

                <div className="lp-flow">
                  <span>Requested</span>
                  <b>→</b>
                  <span>Approved</span>
                  <b>→</b>
                  <span>PO</span>
                </div>

                <span>
                  12 items · required Friday
                </span>
              </div>

              <div className="lp-tour-cap">
                <b>Operational workflow</b>
                <span>
                  Request → approval → purchase → receipt
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        className="lp-section lp-section-alt"
        id="workflow"
      >
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              THE WORKFLOW
            </p>

            <h2>
              Every module earns its place by moving the project forward.
            </h2>
          </div>

          <div className="lp-flowline">
            <div>
              <span>01</span>
              <b>Plan</b>
              <p>
                Organization, projects, clients, milestones and approved
                budget.
              </p>
            </div>

            <div>
              <span>02</span>
              <b>Execute</b>
              <p>
                Daily site reports turn physical work into a reliable
                progress record.
              </p>
            </div>

            <div>
              <span>03</span>
              <b>Source</b>
              <p>
                Material requests and approvals connect operational need to
                procurement.
              </p>
            </div>

            <div>
              <span>04</span>
              <b>Receive</b>
              <p>
                Goods receipts establish what actually arrived and was
                accepted.
              </p>
            </div>

            <div>
              <span>05</span>
              <b>Control</b>
              <p>
                Approved expenses and commitments reveal the project-cost
                picture.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="lp-section" id="teams">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              BUILT FOR THE PEOPLE DOING THE WORK
            </p>

            <h2>
              One system, different views of the same project.
            </h2>
          </div>

          <div className="lp-role-grid">
            {roles.map(([icon, title, desc]) => (
              <article
                className="lp-role"
                key={title}
              >
                <span className="lp-role-icon">
                  <Icon name={icon} />
                </span>

                <h3>{title}</h3>

                <p>{desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section lp-section-cap">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              CORE CAPABILITIES
            </p>

            <h2>
              Focused enough to stay usable. Connected enough to matter.
            </h2>
          </div>

          <div className="lp-cap-grid">
            {capabilities.map(([icon, title, desc]) => (
              <article
                className="lp-cap"
                key={title}
              >
                <span className="lp-role-icon">
                  <Icon name={icon} />
                </span>

                <h3>{title}</h3>

                <p>{desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-cta">
        <div className="lp-wrap">
          <p className="lp-eyebrow">
            START WITH A CLEAR RECORD
          </p>

          <h2>
            Build the project picture from the ground up.
          </h2>

          <p>
            Set up your organization, bring your team in and start connecting
            the work.
          </p>

          <div className="lp-actions lp-actions-center">
            <Link
              to="/register"
              className="lp-btn lp-btn-primary lp-btn-large"
            >
              Get started with Trace
              <Icon name="arrow" />
            </Link>

            <Link
              to="/login"
              className="lp-btn lp-btn-ghost lp-btn-large"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-wrap">
          <div className="lp-foot-top">
            <div>
              <Link
                to="/"
                className="lp-logo"
              >
                <span className="lp-logo-mark">T</span>
                <span>Trace</span>
              </Link>

              <p>
                Construction intelligence for a clearer project record.
              </p>
            </div>

            <div className="lp-newsletter">
              <span>
                Keep up with the build
              </span>

              <div>
                <input
                  aria-label="Email"
                  placeholder="Work email"
                />

                <button
                  type="button"
                  aria-label="Submit"
                >
                  <Icon name="arrow" />
                </button>
              </div>
            </div>
          </div>

          <div className="lp-foot-cols">
            <div>
              <small>PRODUCT</small>
              <a href="#product">Overview</a>
              <a href="#workflow">Workflow</a>
              <a href="#teams">Teams</a>
            </div>

            <div>
              <small>ACCESS</small>
              <Link to="/login">Sign in</Link>
              <Link to="/register">Get started</Link>
            </div>

            <div>
              <small>LANGUAGE</small>
              <button type="button">English</button>
              <button type="button">اردو</button>
            </div>

            <div>
              <small>STATUS</small>

              <span className="lp-status">
                <i />
                Core platform
              </span>
            </div>
          </div>

          <div className="lp-foot-bottom">
            <span>
              © {new Date().getFullYear()} Trace. Construction Intelligence.
            </span>

            <span>
              EN / UR ready
            </span>
          </div>
        </div>
      </footer>
    </main>
  );
}