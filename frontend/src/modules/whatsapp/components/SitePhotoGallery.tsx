import { useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../../organizations/components/OrganizationUi";
import { useProjects } from "../../projects";
import { useSitePhotos } from "../hooks";
import type { SitePhotoListParams } from "../types/whatsapp.types";
import { SitePhotoCard } from "./SitePhotoCard";
import { SitePhotoDetailDialog } from "./SitePhotoDetailDialog";

interface SitePhotoGalleryProps {
  projectId?: string;
  canManage: boolean;
}

export function SitePhotoGallery({ projectId, canManage }: SitePhotoGalleryProps) {
  const [tagFilter, setTagFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [unassignedOnly, setUnassignedOnly] = useState(false);
  const [viewingPhotoId, setViewingPhotoId] = useState<string | null>(null);

  const params: SitePhotoListParams = {
    projectId,
    tag: tagFilter.trim() || undefined,
    photoDateFrom: dateFrom || undefined,
    photoDateTo: dateTo || undefined,
    unassignedOnly: unassignedOnly || undefined,
  };

  const photosQuery = useSitePhotos(params);
  const projectsQuery = useProjects();

  const projects = projectsQuery.data ?? [];
  const projectMap = new Map(projects.map((project) => [project.id, project.name]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <input
          className="w-[160px] rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12.5px] outline-none focus-visible:border-[var(--color-trace-gold-dark)]"
          placeholder="Filter by tag"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          aria-label="Filter photos by tag"
        />
        <input
          type="date"
          className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px] outline-none focus-visible:border-[var(--color-trace-gold-dark)]"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          aria-label="Filter photos from date"
        />
        <span className="text-[12px] text-[var(--color-text-muted)]">to</span>
        <input
          type="date"
          className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px] outline-none focus-visible:border-[var(--color-trace-gold-dark)]"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          aria-label="Filter photos to date"
        />
        <label className="ml-auto flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={unassignedOnly} onChange={(e) => setUnassignedOnly(e.target.checked)} className="accent-[var(--color-trace-gold)]" />
          Needs project only
        </label>
      </div>

      {photosQuery.isLoading ? (
        <LoadingState label="Loading site photos…" />
      ) : photosQuery.isError ? (
        <ErrorState title="Couldn't load site photos" onRetry={() => void photosQuery.refetch()} />
      ) : (photosQuery.data ?? []).length === 0 ? (
        <EmptyState icon="site" title="No site photos" description="Photos sent to the connected WhatsApp number will appear here." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {(photosQuery.data ?? []).map((photo) => (
            <SitePhotoCard
              key={photo.id}
              photo={photo}
              projectName={photo.project_id ? projectMap.get(photo.project_id) : undefined}
              onClick={() => setViewingPhotoId(photo.id)}
            />
          ))}
        </div>
      )}

      {viewingPhotoId ? (
        <SitePhotoDetailDialog photoId={viewingPhotoId} projects={projects} canManage={canManage} onClose={() => setViewingPhotoId(null)} />
      ) : null}
    </div>
  );
}