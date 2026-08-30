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
      className="group flex flex-col overflow-hidden rounded-[11px] border border-[#e1d5bc] bg-white text-left transition hover:border-[#cdbd9c] hover:shadow-[0_8px_22px_rgba(90,70,40,0.08)]"
    >
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-[#f5efe3]">
        <img src={photo.photo_url} alt="" className="h-full w-full object-cover transition group-hover:scale-[1.03]" loading="lazy" />
        {!photo.project_id ? (
          <span className="absolute left-2 top-2 rounded-full bg-[#c24a3a] px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.06em] text-white">
            Needs project
          </span>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-[11px] font-semibold text-[#191410]">{projectName ?? "Unassigned"}</span>
          <span className="shrink-0 text-[9.5px] text-[#a2957c]">{formatPhotoDate(photo.photo_date)}</span>
        </div>

        {photo.location_text ? (
          <div className="flex items-center gap-1 truncate text-[10px] text-[#6b6152]">
            <Icon name="info" size={10} />
            {photo.location_text}
          </div>
        ) : null}

        {photo.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {photo.tags.slice(0, 3).map((tag) => (
              <Badge key={tag.id} tone={tag.source === "AI" ? "blue" : "slate"}>{tag.tag}</Badge>
            ))}
            {photo.tags.length > 3 ? <span className="text-[9px] text-[#a2957c]">+{photo.tags.length - 3}</span> : null}
          </div>
        ) : null}
      </div>
    </button>
  );
}