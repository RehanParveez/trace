import { Badge, Icon } from "../../organizations/components/OrganizationUi";
import type { SitePhoto } from "../types/whatsapp.types";
import { formatPhotoDate } from "../utils/whatsapp.utils";

interface SitePhotoCardProps {
  photo: SitePhoto;
  projectName?: string;
  onClick: () => void;
}

export function SitePhotoCard({ photo, projectName, onClick }: SitePhotoCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] text-left transition hover:border-[var(--color-border-strong)] hover:shadow-[0_8px_22px_rgba(90,70,40,0.08)]"
    >
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-[var(--color-surface-muted)]">
        <img src={photo.photo_url} alt="" className="h-full w-full object-cover transition group-hover:scale-[1.03]" loading="lazy" />
        {!photo.project_id ? (
          <span className="absolute left-2 top-2 rounded-full bg-[var(--color-danger)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-white">
            Needs project
          </span>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-[12.5px] font-semibold text-[var(--color-text-primary)]">{projectName ?? "Unassigned"}</span>
          <span className="shrink-0 text-[11px] text-[var(--color-text-muted)]">{formatPhotoDate(photo.photo_date)}</span>
        </div>

        {photo.location_text ? (
          <div className="flex items-center gap-1 truncate text-[11.5px] text-[var(--color-text-secondary)]">
            <Icon name="info" size={10} />
            {photo.location_text}
          </div>
        ) : null}

        {photo.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {photo.tags.slice(0, 3).map((tag) => (
              <Badge key={tag.id} tone={tag.source === "AI" ? "blue" : "slate"}>{tag.tag}</Badge>
            ))}
            {photo.tags.length > 3 ? <span className="text-[11px] text-[var(--color-text-muted)]">+{photo.tags.length - 3}</span> : null}
          </div>
        ) : null}
      </div>
    </button>
  );
}