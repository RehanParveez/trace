import { useState } from "react";
import { Button, Icon } from "../../organizations/components/OrganizationUi";
import { useSitePhotos } from "../../whatsapp";
import { useCreatePhotoBOQLink, useDeletePhotoBOQLink, usePhotoBOQLinks } from "../hooks";

interface PhotoEvidencePickerProps {
  claimId: string;
  projectId: string;
  boqItemId: string;
  canManage: boolean;
}

export function PhotoEvidencePicker({ claimId, projectId, boqItemId, canManage }: PhotoEvidencePickerProps) {
  const linksQuery = usePhotoBOQLinks(claimId);
  const photosQuery = useSitePhotos({ projectId });
  const createLink = useCreatePhotoBOQLink(claimId);
  const deleteLink = useDeletePhotoBOQLink(claimId);
  const [picking, setPicking] = useState(false);

  const links = linksQuery.data ?? [];
  const linkedPhotoIds = new Set(links.map((link) => link.site_photo_id));
  const photos = photosQuery.data ?? [];
  const linkedPhotos = photos.filter((photo) => linkedPhotoIds.has(photo.id));
  const availablePhotos = photos.filter((photo) => !linkedPhotoIds.has(photo.id));

  return (
    <div>
     <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">Photo evidence</span>
        {canManage ? (
          <button type="button" onClick={() => setPicking((v) => !v)} className="text-[12px] font-semibold text-[var(--color-trace-gold-dark)] hover:text-[var(--color-warning)]">
            {picking ? "Done" : "Attach photo"}
          </button>
        ) : null}
      </div>

      {linkedPhotos.length === 0 ? (
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-[12px] text-[var(--color-text-secondary)]">No photos attached yet.</div>
      ) : (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {linkedPhotos.map((photo) => {
            const link = links.find((l) => l.site_photo_id === photo.id);
            return (
             <div key={photo.id} className="group relative overflow-hidden rounded-[8px] border border-[var(--color-border)]">
                <img src={photo.photo_url} alt="" className="aspect-square w-full object-cover" />
                {canManage && link ? (
                  <button
                    type="button"
                    onClick={() => deleteLink.mutate(link.id)}
                    className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-trace-navy)]/70 text-white opacity-0 transition group-hover:opacity-100"
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
        <div className="mt-3 max-h-56 overflow-y-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] p-2">
          {availablePhotos.length === 0 ? (
            <div className="p-2 text-[12px] text-[var(--color-text-muted)]">No unattached photos found for this project.</div>
          ) : (
            <div className="grid grid-cols-4 gap-2 sm:grid-cols-5">
              {availablePhotos.map((photo) => (
                <button
                  key={photo.id}
                  type="button"
                  onClick={() =>
                    createLink.mutate({ progress_claim_id: claimId, site_photo_id: photo.id, boq_item_id: boqItemId })
                  }
                  className="overflow-hidden rounded-[6px] border border-[var(--color-border)] transition hover:border-[var(--color-trace-gold-dark)]"
                >
                  <img src={photo.photo_url} alt="" className="aspect-square w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}