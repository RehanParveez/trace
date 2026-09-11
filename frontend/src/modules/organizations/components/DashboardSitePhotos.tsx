import { Link } from "react-router-dom";
import { Icon, Panel, PanelHeader } from "./OrganizationUi";
import { formatRelativeTime } from "../utils/organization.utils";
import { useSitePhotos } from "../../whatsapp";
import { useProjects } from "../../projects";

export function DashboardSitePhotos() {
  const photosQuery = useSitePhotos({ limit: 8 });
  const projectsQuery = useProjects();

  const photos = photosQuery.data ?? [];
  const projects = projectsQuery.data ?? [];
  const projectNameById = new Map(projects.map((project) => [project.id, project.name]));

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        eyebrow="FROM THE FIELD"
        title="Recent site photos"
        description="The latest photos sent in from site over WhatsApp, filed automatically by Trace."
      />

      {photosQuery.isLoading ? (
        <div className="px-5 py-8 text-[13px] text-[var(--color-text-secondary)] sm:px-6">
          Loading recent photos…
        </div>
      ) : photos.length === 0 ? (
        <div className="flex items-center gap-3 px-5 py-8 sm:px-6">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]">
            <Icon name="site" size={16} />
          </div>
          <p className="text-[13px] text-[var(--color-text-secondary)]">
            No site photos yet. Connect a WhatsApp number so field teams can start sending progress photos.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2.5 p-4 sm:grid-cols-4 sm:p-5">
          {photos.map((photo) => (
            <Link
              key={photo.id}
              to="/app/site-photos"
              className="group relative aspect-square overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)] focus-visible:ring-offset-2"
            >
              <img
                src={photo.photo_url}
                alt=""
                className="h-full w-full object-cover transition group-hover:scale-[1.04]"
                loading="lazy"
              />

              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-[linear-gradient(0deg,rgba(8,13,24,0.75),transparent)] p-2">
                <span className="block truncate text-[10.5px] font-semibold text-white">
                  {photo.project_id ? (projectNameById.get(photo.project_id) ?? "Unknown project") : "Unassigned"}
                </span>
                <span className="block text-[9px] text-white/70">
                  {formatRelativeTime(photo.created_at)}
                </span>
              </div>

              {!photo.project_id ? (
                <span className="absolute right-1.5 top-1.5 rounded-full bg-[var(--color-danger)] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.04em] text-white">
                  Needs project
                </span>
              ) : null}
            </Link>
          ))}
        </div>
      )}

      <div className="border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-3 sm:px-6">
        <Link
          to="/app/site-photos"
          className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline"
        >
          View all site photos
          <Icon name="arrow" size={12} />
        </Link>
      </div>
    </Panel>
  );
}