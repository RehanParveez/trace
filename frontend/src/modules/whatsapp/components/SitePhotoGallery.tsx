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
      <div className="flex flex-wrap items-center gap-2 rounded-[10px] border border-[#e1d5bc] bg-white p-3">
        <input
          className="w-[150px] rounded-[7px] border border-[#d9ceb9] bg-white px-2.5 py-1.5 text-[11px] outline-none focus:border-[#c39a38]"
          placeholder="Filter by tag"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
        />
        <input
          type="date"
          className="rounded-[7px] border border-[#d9ceb9] bg-white px-2.5 py-1.5 text-[10.5px] outline-none focus:border-[#c39a38]"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <span className="text-[10px] text-[#a2957c]">to</span>
        <input
          type="date"
          className="rounded-[7px] border border-[#d9ceb9] bg-white px-2.5 py-1.5 text-[10.5px] outline-none focus:border-[#c39a38]"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
        <label className="ml-auto flex items-center gap-1.5 text-[10.5px] text-[#6b6152]">
          <input type="checkbox" checked={unassignedOnly} onChange={(e) => setUnassignedOnly(e.target.checked)} />
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