import { useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Icon, Modal } from "../../organizations/components/OrganizationUi";
import { useAddPhotoTag, useAssignProject, useRemovePhotoTag, useSitePhoto, useUpdateSitePhoto } from "../hooks";
import type { Project } from "../../projects";
import { formatCapturedAt, formatPhoneNumber, getCaptionField } from "../utils/whatsapp.utils";

interface SitePhotoDetailDialogProps {
  photoId: string;
  projects: Project[];
  canManage: boolean;
  onClose: () => void;
}

export function SitePhotoDetailDialog({ photoId, projects, canManage, onClose }: SitePhotoDetailDialogProps) {
  const photoQuery = useSitePhoto(photoId);
  const assignProject = useAssignProject();
  const updatePhoto = useUpdateSitePhoto();
  const addTag = useAddPhotoTag(photoId);
  const removeTag = useRemovePhotoTag(photoId);

  const [newTag, setNewTag] = useState("");
  const [locationDraft, setLocationDraft] = useState<string | null>(null);

  const photo = photoQuery.data;

  function submitTag(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTag.trim()) return;
    addTag.mutate({ tag: newTag.trim() }, { onSuccess: () => setNewTag("") });
  }

  if (photoQuery.isLoading || !photo) {
    return (
      <Modal title="Site photo" onClose={onClose}>
        <div className="py-8 text-center text-[11px] text-[#6b6152]">Loading…</div>
      </Modal>
    );
  }

  const location = locationDraft ?? photo.location_text ?? "";
  const noteText = getCaptionField(photo.caption_parsed, "notes");

  return (
    <Modal title="Site photo" description={formatCapturedAt(photo.created_at)} onClose={onClose} wide>
      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <img src={photo.photo_url} alt="" className="w-full rounded-[10px] border border-[#e1d5bc] object-cover" />

        <div className="space-y-4">
          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Sender</div>
            <div className="mt-1 text-[12.5px] font-semibold text-[#191410]">{formatPhoneNumber(photo.sender_phone_number)}</div>
          </div>

          {photo.caption_raw ? (
            <div>
              <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Caption</div>
              <div className="mt-1 text-[11.5px] leading-5 text-[#332a21]">{photo.caption_raw}</div>
              {noteText ? <div className="mt-1 text-[10.5px] italic text-[#756957]">AI notes: {noteText}</div> : null}
            </div>
          ) : null}

          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Project</div>
            {canManage ? (
              <select
                className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
                value={photo.project_id ?? ""}
                onChange={(event) => {
                  if (!event.target.value) return;
                  assignProject.mutate({ photoId, payload: { project_id: event.target.value } });
                }}
              >
                <option value="" disabled>Select a project…</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            ) : (
              <div className="mt-1 text-[11.5px] font-semibold text-[#191410]">
                {projects.find((p) => p.id === photo.project_id)?.name ?? "Unassigned"}
              </div>
            )}
          </div>

          {canManage ? (
            <div>
              <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Location</div>
              <div className="mt-1.5 flex gap-2">
                <input
                  className="w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
                  value={location}
                  onChange={(e) => setLocationDraft(e.target.value)}
                  placeholder="e.g. Block C, Level 3"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={updatePhoto.isPending}
                  onClick={() => updatePhoto.mutate({ photoId, payload: { location_text: location || null } }, { onSuccess: () => setLocationDraft(null) })}
                >
                  Save
                </Button>
              </div>
            </div>
          ) : photo.location_text ? (
            <div>
              <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Location</div>
              <div className="mt-1 text-[11.5px] text-[#191410]">{photo.location_text}</div>
            </div>
          ) : null}

          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#a2957c]">Tags</div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {photo.tags.map((tag) => (
                <span key={tag.id} className="inline-flex items-center gap-1.5 rounded-full bg-[#efe6d3] px-2.5 py-1 text-[10.5px] font-semibold text-[#6b6152]">
                  {tag.tag}
                  {tag.source === "AI" ? <Badge tone="blue">AI</Badge> : null}
                  {canManage ? (
                    <button type="button" onClick={() => removeTag.mutate(tag.id)} className="text-[#a2957c] hover:text-[#c24a3a]">
                      <Icon name="x" size={9} />
                    </button>
                  ) : null}
                </span>
              ))}
              {photo.tags.length === 0 ? <span className="text-[10.5px] text-[#a2957c]">No tags yet.</span> : null}
            </div>

            {canManage ? (
              <form onSubmit={submitTag} className="mt-2 flex gap-2">
                <input
                  className="w-full rounded-[7px] border border-[#d9ceb9] bg-white px-2.5 py-1.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder="Add a tag"
                />
                <Button type="submit" variant="secondary" size="sm" disabled={!newTag.trim() || addTag.isPending}>Add</Button>
              </form>
            ) : null}
          </div>
        </div>
      </div>
    </Modal>
  );
}