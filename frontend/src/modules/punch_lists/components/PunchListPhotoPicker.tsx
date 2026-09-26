import { useState } from "react";
import { Badge, Button, Icon } from "../../organizations/components/OrganizationUi";
import { useSitePhotos } from "../../whatsapp";
import { useAddPunchListPhoto, useRemovePunchListPhoto } from "../hooks";
import type { PunchListItem, PunchListPhotoPurpose } from "../types/punch-list.types";

export function PunchListPhotoPicker({ projectId, punchListId, item, canManage }: {
  projectId: string; punchListId: string; item: PunchListItem; canManage: boolean;
}) {
  const [picking, setPicking] = useState(false);
  const [purpose, setPurpose] = useState<PunchListPhotoPurpose>("DEFECT");
  const photosQuery = useSitePhotos({ projectId });
  const addPhoto = useAddPunchListPhoto(projectId, punchListId);
  const removePhoto = useRemovePunchListPhoto(projectId, punchListId);

  const linkedPhotoIds = new Set(item.photos.map((p) => p.site_photo_id));
  const availablePhotos = (photosQuery.data ?? []).filter((p) => !linkedPhotoIds.has(p.id));

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">Photos</span>
        {canManage ? (
          <button type="button" onClick={() => setPicking((v) => !v)} className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] hover:underline">
            {picking ? "Done" : "Attach photo"}
          </button>
        ) : null}
      </div>

      {item.photos.length === 0 ? (
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">No photos attached yet.</div>
      ) : (
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
          {item.photos.map((link) => {
            const photo = (photosQuery.data ?? []).find((p) => p.id === link.site_photo_id);
            return (
              <div key={link.id} className="group relative overflow-hidden rounded-[8px] border border-[var(--color-border)]">
                {photo ? <img src={photo.photo_url} alt="" className="aspect-square w-full object-cover" /> : null}
                <Badge tone={link.photo_purpose === "DEFECT" ? "red" : "green"}>{link.photo_purpose === "DEFECT" ? "Defect" : "Fixed"}</Badge>
                {canManage ? (
                  <button
                    type="button"
                    onClick={() => removePhoto.mutate(link.id)}
                    className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-trace-navy)]/70 text-white opacity-0 outline-none transition focus-visible:opacity-100 group-hover:opacity-100"
                  >
                    <Icon name="x" size={10} />
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {picking ? (
        <div className="mt-3 space-y-2">
          <div className="flex gap-2">
            <button type="button" onClick={() => setPurpose("DEFECT")} className={`flex-1 rounded-[6px] border px-2 py-1.5 text-[11.5px] font-semibold ${purpose === "DEFECT" ? "border-[var(--color-danger)] bg-[var(--color-danger-bg)]" : "border-[var(--color-border)]"}`}>Defect photo</button>
            <button type="button" onClick={() => setPurpose("RESOLUTION")} className={`flex-1 rounded-[6px] border px-2 py-1.5 text-[11.5px] font-semibold ${purpose === "RESOLUTION" ? "border-[var(--color-success)] bg-[var(--color-success-bg)]" : "border-[var(--color-border)]"}`}>Resolution photo</button>
          </div>
          <div className="max-h-48 overflow-y-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-2">
            {availablePhotos.length === 0 ? (
              <div className="p-2 text-[11.5px] text-[var(--color-text-muted)]">No unattached photos found for this project.</div>
            ) : (
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                {availablePhotos.map((photo) => (
                  <button
                    key={photo.id}
                    type="button"
                    onClick={() => addPhoto.mutate({ itemId: item.id, sitePhotoId: photo.id, purpose })}
                    className="overflow-hidden rounded-[6px] border border-[var(--color-border)] transition hover:border-[var(--color-trace-gold-dark)]"
                  >
                    <img src={photo.photo_url} alt="" className="aspect-square w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}