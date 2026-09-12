import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "../../shared/components/LanguageSwitcher";
import "../home/landing.css";

type IconName =
  | "flow"
  | "budget"
  | "site"
  | "materials"
  | "lock"
  | "arrow"
  | "chart"
  | "team";

function Icon({ name }: { name: IconName }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  const paths: Record<IconName, ReactNode> = {
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

const capabilityKeys = [
  ["budget", "budgetControl"],
  ["site", "siteProgress"],
  ["materials", "procurement"],
  ["chart", "costVisibility"],
] as const satisfies ReadonlyArray<readonly [IconName, string]>;

const roleKeys = [
  ["team", "leadership"],
  ["site", "siteTeams"],
  ["materials", "procurement"],
  ["budget", "finance"],
] as const satisfies ReadonlyArray<readonly [IconName, string]>;

function DashboardMockup() {
  return (
    <div className="lp-dashboard">
      <aside className="lp-dash-nav">
        <div className="lp-dash-nav-brand">
          <span className="lp-mini-mark">T</span>
          <span>Trace</span>
        </div>

        <div className="lp-dash-nav-group">
          <small>WORKSPACE</small>
          <span className="active">Overview</span>
        </div>

        <div className="lp-dash-nav-group">
          <small>PROJECTS</small>
          <span>Projects</span>
          <span>Budgets</span>
          <span>Procurement</span>
          <span>Expenses</span>
        </div>

        <div className="lp-dash-nav-group">
          <small>INTELLIGENCE</small>
          <span>AI activity</span>
          <span>Audit log</span>
        </div>
      </aside>

      <div className="lp-dash-main">
        <div className="lp-dash-heading">
          <div>
            <small>GOOD MORNING</small>
            <strong>Metro Builders</strong>
          </div>

          <span className="lp-demo-pill">
            LIVE WORKSPACE
          </span>
        </div>

        <div className="lp-kpis">
          <div>
            <small>APPROVED BUDGET</small>
            <b>Rs 84.6M</b>
          </div>

          <div>
            <small>COMMITTED</small>
            <b>Rs 12.4M</b>
          </div>

          <div>
            <small>SPENT</small>
            <b>Rs 38.9M</b>
          </div>

          <div>
            <small>REMAINING</small>
            <b className="lp-kpi-good">Rs 33.3M</b>
          </div>
        </div>

        <div className="lp-dash-grid">
          <div className="lp-project-card">
            <div className="lp-card-head">
              <b>Project health</b>
              <span>6 active</span>
            </div>

            <div className="lp-project-row">
              <span>Shopping Plaza</span>
              <div className="lp-mini-bar">
                <i style={{ width: "72%" }} />
              </div>
              <b>72%</b>
            </div>

            <div className="lp-project-row">
              <span>Faisalabad Warehouse</span>
              <div className="lp-mini-bar">
                <i style={{ width: "41%" }} />
              </div>
              <b>41%</b>
            </div>

            <div className="lp-project-row">
              <span>Gulberg Residential</span>
              <div className="lp-mini-bar">
                <i style={{ width: "88%" }} />
              </div>
              <b>88%</b>
            </div>
          </div>

          <div className="lp-attention-card">
            <div className="lp-card-head">
              <b>Needs attention</b>
              <span>4 open</span>
            </div>

            <div className="lp-attention-row">
              <i className="lp-dot-gold" />
              3 progress claims awaiting review
            </div>

            <div className="lp-attention-row">
              <i className="lp-dot-gold" />
              7 material mappings need attention
            </div>

            <div className="lp-attention-row">
              <i className="lp-dot-gold" />
              2 procurement requests pending
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function HomePage() {
  const { t } = useTranslation();

  return (
    <main className="lp-page">
      <nav className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <Link to="/" className="lp-logo">
            <span className="lp-logo-mark">T</span>
            <span>Trace</span>
          </Link>

          <div className="lp-nav-links">
            <a href="#product">{t("nav.product")}</a>
            <a href="#workflow">{t("nav.workflow")}</a>
            <a href="#teams">{t("nav.teams")}</a>
            <a href="#principles">{t("nav.why")}</a>
          </div>

          <div className="lp-nav-actions">
            <span className="lp-live">
              <i />
              {t("nav.operational")}
            </span>

            <LanguageSwitcher
              variant="compact"
              className="mr-2"
            />

            <Link
              to="/login"
              className="lp-btn lp-btn-ghost"
            >
              {t("nav.signIn")}
            </Link>

            <Link
              to="/register"
              className="lp-btn lp-btn-primary"
            >
              {t("nav.getStarted")}
            </Link>
          </div>
        </div>
      </nav>

      <section className="lp-hero">
        <div className="lp-wrap lp-hero-grid">
          <div className="lp-hero-copy">
            <p className="lp-eyebrow">
              {t("hero.eyebrow")}
            </p>

            <h1>
              {t("hero.title")}
            </h1>

            <p className="lp-hero-sub">
              {t("hero.sub")}
            </p>

            <div className="lp-actions">
              <Link
                to="/register"
                className="lp-btn lp-btn-primary lp-btn-large"
              >
                {t("hero.ctaPrimary")}
                <Icon name="arrow" />
              </Link>

              <a
                href="#product"
                className="lp-btn lp-btn-ghost lp-btn-large"
              >
                {t("hero.ctaSecondary")}
              </a>
            </div>

            <div className="lp-proof">
              <span>
                <Icon name="lock" />
                {t("hero.proof.permission")}
              </span>

              <span>
                <Icon name="flow" />
                {t("hero.proof.workflow")}
              </span>

              <span>
                <Icon name="chart" />
                {t("hero.proof.backend")}
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
            {t("stat.heading")}
          </div>

          <p>
            {t("stat.description")}
          </p>

          <div className="lp-tags">
            <span>
              <Icon name="budget" />
              {t("stat.tags.budget")}
            </span>

            <span>
              <Icon name="site" />
              {t("stat.tags.progress")}
            </span>

            <span>
              <Icon name="materials" />
              {t("stat.tags.procurement")}
            </span>

            <span>
              <Icon name="materials" />
              {t("stat.tags.receipts")}
            </span>

            <span>
              <Icon name="chart" />
              {t("stat.tags.cost")}
            </span>
          </div>

          <div className="lp-origin">
            <b>T</b>

            <p>
              {t("stat.origin")}
            </p>
          </div>
        </div>
      </section>

      <section className="lp-section" id="product">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              {t("product.eyebrow")}
            </p>

            <h2>
              {t("product.heading")}
            </h2>
          </div>

          <div className="lp-tour">
            <div className="lp-tour-main">
              <DashboardMockup />

              <div className="lp-tour-cap">
                <b>
                  {t("product.tour.main.title")}
                </b>

                <span>
                  {t("product.tour.main.caption")}
                </span>
              </div>
            </div>

            <div className="lp-tour-small">
              <div className="lp-mini-panel">
                <small>
                  {t("product.tour.financial.label")}
                </small>

                <strong>
                  {t("product.tour.financial.amount")}
                </strong>

                <div className="lp-meter">
                  <i
                    style={{
                      width: `${t(
                        "product.tour.financial.progress",
                      )}%`,
                    }}
                  />
                </div>

                <span>
                  {t("product.tour.financial.status")}
                </span>
              </div>

              <div className="lp-tour-cap">
                <b>
                  {t("product.tour.financial.title")}
                </b>

                <span>
                  {t("product.tour.financial.caption")}
                </span>
              </div>
            </div>

            <div className="lp-tour-small">
              <div className="lp-mini-panel">
                <small>
                  {t("product.tour.workflow.label")}
                </small>

                <strong>
                  {t("product.tour.workflow.requestId")}
                </strong>

                <div className="lp-flow">
                  <span>
                    {t(
                      "product.tour.workflow.steps.requested",
                    )}
                  </span>

                  <b>→</b>

                  <span>
                    {t(
                      "product.tour.workflow.steps.approved",
                    )}
                  </span>

                  <b>→</b>

                  <span>
                    {t(
                      "product.tour.workflow.steps.purchaseOrder",
                    )}
                  </span>
                </div>

                <span>
                  {t("product.tour.workflow.items")}
                </span>
              </div>

              <div className="lp-tour-cap">
                <b>
                  {t("product.tour.workflow.title")}
                </b>

                <span>
                  {t("product.tour.workflow.caption")}
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
              {t("workflow.eyebrow")}
            </p>

            <h2>
              {t("workflow.heading")}
            </h2>
          </div>

          <div className="lp-flowline">
            <div>
              <span>01</span>

              <b>
                {t("workflow.steps.plan.title")}
              </b>

              <p>
                {t("workflow.steps.plan.description")}
              </p>
            </div>

            <div>
              <span>02</span>

              <b>
                {t("workflow.steps.execute.title")}
              </b>

              <p>
                {t("workflow.steps.execute.description")}
              </p>
            </div>

            <div>
              <span>03</span>

              <b>
                {t("workflow.steps.source.title")}
              </b>

              <p>
                {t("workflow.steps.source.description")}
              </p>
            </div>

            <div>
              <span>04</span>

              <b>
                {t("workflow.steps.receive.title")}
              </b>

              <p>
                {t("workflow.steps.receive.description")}
              </p>
            </div>

            <div>
              <span>05</span>

              <b>
                {t("workflow.steps.control.title")}
              </b>

              <p>
                {t("workflow.steps.control.description")}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="lp-section" id="teams">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              {t("teams.eyebrow")}
            </p>

            <h2>
              {t("teams.heading")}
            </h2>
          </div>

          <div className="lp-role-grid">
            {roleKeys.map(([icon, key]) => (
              <article
                className="lp-role"
                key={key}
              >
                <span className="lp-role-icon">
                  <Icon name={icon} />
                </span>

                <h3>
                  {t(`teams.roles.${key}.title`)}
                </h3>

                <p>
                  {t(`teams.roles.${key}.description`)}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section lp-section-cap">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <p className="lp-eyebrow">
              {t("capabilities.eyebrow")}
            </p>

            <h2>
              {t("capabilities.heading")}
            </h2>
          </div>

          <div className="lp-cap-grid">
            {capabilityKeys.map(([icon, key]) => (
              <article
                className="lp-cap"
                key={key}
              >
                <span className="lp-role-icon">
                  <Icon name={icon} />
                </span>

                <h3>
                  {t(`capabilities.items.${key}.title`)}
                </h3>

                <p>
                  {t(
                    `capabilities.items.${key}.description`,
                  )}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-cta">
        <div className="lp-wrap">
          <p className="lp-eyebrow">
            {t("cta.eyebrow")}
          </p>

          <h2>
            {t("cta.heading")}
          </h2>

          <p>
            {t("cta.description")}
          </p>

          <div className="lp-actions lp-actions-center">
            <Link
              to="/register"
              className="lp-btn lp-btn-primary lp-btn-large"
            >
              {t("cta.ctaPrimary")}
              <Icon name="arrow" />
            </Link>

            <Link
              to="/login"
              className="lp-btn lp-btn-ghost lp-btn-large"
            >
              {t("nav.signIn")}
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
                {t("footer.tagline")}
              </p>
            </div>

            <div className="lp-newsletter">
              <span>
                {t("footer.newsletter.label")}
              </span>

              <div>
                <input
                  aria-label={t(
                    "footer.newsletter.emailLabel",
                  )}
                  placeholder={t(
                    "footer.newsletter.placeholder",
                  )}
                />

                <button
                  type="button"
                  aria-label={t(
                    "footer.newsletter.submitLabel",
                  )}
                >
                  <Icon name="arrow" />
                </button>
              </div>
            </div>
          </div>

          <div className="lp-foot-cols">
            <div>
              <small>
                {t("footer.columns.product.label")}
              </small>

              <a href="#product">
                {t("footer.columns.product.overview")}
              </a>

              <a href="#workflow">
                {t("nav.workflow")}
              </a>

              <a href="#teams">
                {t("nav.teams")}
              </a>
            </div>

            <div>
              <small>
                {t("footer.columns.access.label")}
              </small>

              <Link to="/login">
                {t("nav.signIn")}
              </Link>

              <Link to="/register">
                {t("footer.columns.access.getStarted")}
              </Link>
            </div>

            <div>
              <small>
                {t("footer.columns.language.label")}
              </small>

              <LanguageSwitcher />
            </div>

            <div>
              <small>
                {t("footer.columns.status.label")}
              </small>

              <span className="lp-status">
                <i />
                {t("footer.columns.status.value")}
              </span>
            </div>
          </div>

          <div className="lp-foot-bottom">
            <span>
              {t("footer.copyright", {
                year: new Date().getFullYear(),
              })}
            </span>

            <span>
              {t("footer.ready")}
            </span>
          </div>
        </div>
      </footer>
    </main>
  );
}