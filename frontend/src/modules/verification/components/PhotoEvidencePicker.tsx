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
        <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Photo evidence</span>
        {canManage ? (
          <button type="button" onClick={() => setPicking((v) => !v)} className="text-[10.5px] font-semibold text-[#b98626] hover:text-[#9a6f1c]">
            {picking ? "Done" : "Attach photo"}
          </button>
        ) : null}
      </div>

      {linkedPhotos.length === 0 ? (
        <div className="rounded-[8px] border border-[#e1d5bc] bg-white px-3 py-2.5 text-[11px] text-[#6b6152]">No photos attached yet.</div>
      ) : (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {linkedPhotos.map((photo) => {
            const link = links.find((l) => l.site_photo_id === photo.id);
            return (
              <div key={photo.id} className="group relative overflow-hidden rounded-[8px] border border-[#e1d5bc]">
                <img src={photo.photo_url} alt="" className="aspect-square w-full object-cover" />
                {canManage && link ? (
                  <button
                    type="button"
                    onClick={() => deleteLink.mutate(link.id)}
                    className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-[#080d18]/70 text-white opacity-0 transition group-hover:opacity-100"
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
        <div className="mt-3 max-h-56 overflow-y-auto rounded-[8px] border border-[#e1d5bc] bg-white p-2">
          {availablePhotos.length === 0 ? (
            <div className="p-2 text-[10.5px] text-[#a2957c]">No unattached photos found for this project.</div>
          ) : (
            <div className="grid grid-cols-4 gap-2 sm:grid-cols-5">
              {availablePhotos.map((photo) => (
                <button
                  key={photo.id}
                  type="button"
                  onClick={() =>
                    createLink.mutate({ progress_claim_id: claimId, site_photo_id: photo.id, boq_item_id: boqItemId })
                  }
                  className="overflow-hidden rounded-[6px] border border-[#e1d5bc] transition hover:border-[#c39a38]"
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