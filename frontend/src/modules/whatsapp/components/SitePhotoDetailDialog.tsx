import { useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Icon, inputClass, Modal, SectionLabel } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useAddPhotoTag, useAssignProject, useRemovePhotoTag, useSitePhoto, useUpdateSitePhoto,
} from "../hooks";
import type { Project } from "../../projects";
import {formatCapturedAt, formatPhoneNumber, formatPhotoDate, getCaptionField,
} from "../utils/whatsapp.utils";

interface SitePhotoDetailDialogProps {
  photoId: string;
  projects: Project[];
  canManage: boolean;
  onClose: () => void;
}

export function SitePhotoDetailDialog({
  photoId,
  projects,
  canManage,
  onClose,
}: SitePhotoDetailDialogProps) {
  const photoQuery = useSitePhoto(photoId);
  const assignProject = useAssignProject();
  const updatePhoto = useUpdateSitePhoto();
  const addTag = useAddPhotoTag(photoId);
  const removeTag = useRemovePhotoTag(photoId);

  const [newTag, setNewTag] = useState("");
  const [locationDraft, setLocationDraft] = useState<string | null>(null);
  const [dateDraft, setDateDraft] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const photo = photoQuery.data;

  function submitTag(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTag.trim()) return;
    setError(null);
    addTag.mutate(
      { tag: newTag.trim() },
      {
        onSuccess: () => setNewTag(""),
        onError: (mutationError) =>
          setError(
            getApiErrorMessage(
              mutationError,
              "Couldn't add this tag. Please try again.",
            ),
          ),
      },
    );
  }

  if (photoQuery.isLoading || !photo) {
    return (
      <Modal title="Site photo" onClose={onClose}>
        <div className="py-8 text-center text-[12.5px] text-[var(--color-text-secondary)]">
          Loading…
        </div>
      </Modal>
    );
  }
  const location = locationDraft ?? photo.location_text ?? "";
  const photoDate = dateDraft ?? photo.photo_date ?? "";
  const noteText = getCaptionField(photo.caption_parsed, "notes");

  return (
    <Modal
      title="Site photo"
      description={formatCapturedAt(photo.created_at)}
      onClose={onClose}
      wide
    >
      {error ? (
        <div className="mb-4 rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
          {error}
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <img
          src={photo.photo_url}
          alt=""
          className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] object-cover"
        />

        <div className="space-y-4">
          <div>
            <SectionLabel>Sender</SectionLabel>
            <div className="mt-1 text-[13.5px] font-semibold text-[var(--color-text-primary)]">
              {formatPhoneNumber(photo.sender_phone_number)}
            </div>
          </div>

          {photo.caption_raw ? (
            <div>
              <SectionLabel>Caption</SectionLabel>
              <div className="mt-1 text-[13px] leading-5 text-[var(--color-text-primary)]">
                {photo.caption_raw}
              </div>
              {noteText ? (
                <div className="mt-1 text-[12px] italic text-[var(--color-text-secondary)]">
                  AI notes: {noteText}
                </div>
              ) : null}
            </div>
          ) : null}

          <div>
            <SectionLabel>Project</SectionLabel>
            {canManage ? (
              <select
                className={`mt-1.5 ${inputClass}`}
                value={photo.project_id ?? ""}
                onChange={(event) => {
                  if (!event.target.value) return;
                  setError(null);
                  assignProject.mutate(
                    { photoId, payload: { project_id: event.target.value } },
                    {
                      onError: (mutationError) =>
                        setError(
                          getApiErrorMessage(
                            mutationError,
                            "Couldn't assign this photo to a project.",
                          ),
                        ),
                    },
                  );
                }}
              >
                <option value="" disabled>
                  Select a project…
                </option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            ) : (
              <div className="mt-1 text-[13.5px] font-semibold text-[var(--color-text-primary)]">
                {projects.find((p) => p.id === photo.project_id)?.name ??
                  "Unassigned"}
              </div>
            )}
          </div>

          {canManage ? (
            <div>
              <SectionLabel>Location</SectionLabel>
              <div className="mt-1.5 flex gap-2">
                <input
                  className={inputClass}
                  value={location}
                  onChange={(e) => setLocationDraft(e.target.value)}
                  placeholder="e.g. Block C, Level 3"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={updatePhoto.isPending}
                  onClick={() => {
                    setError(null);
                    updatePhoto.mutate(
                      { photoId, payload: { location_text: location || null } },
                      {
                        onSuccess: () => setLocationDraft(null),
                        onError: (mutationError) =>
                          setError(
                            getApiErrorMessage(
                              mutationError,
                              "Couldn't update the location. Please try again.",
                            ),
                          ),
                      },
                    );
                  }}
                >
                  Save
                </Button>
              </div>
            </div>
          ) : photo.location_text ? (
            <div>
              <SectionLabel>Location</SectionLabel>
              <div className="mt-1 text-[13px] text-[var(--color-text-primary)]">
                {photo.location_text}
              </div>
            </div>
          ) : null}

          {canManage ? (
            <div>
              <SectionLabel>Captured date</SectionLabel>
              <div className="mt-1.5 flex gap-2">
                <input
                  type="date"
                  className={inputClass}
                  value={photoDate}
                  onChange={(e) => setDateDraft(e.target.value)}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={updatePhoto.isPending}
                  onClick={() => {
                    setError(null);
                    updatePhoto.mutate(
                      { photoId, payload: { photo_date: photoDate || null } },
                      {
                        onSuccess: () => setDateDraft(null),
                        onError: (mutationError) =>
                          setError(
                            getApiErrorMessage(
                              mutationError,
                              "Couldn't update the date. Please try again.",
                            ),
                          ),
                      },
                    );
                  }}
                >
                  Save
                </Button>
              </div>
            </div>
          ) : photo.photo_date ? (
            <div>
              <SectionLabel>Captured date</SectionLabel>
              <div className="mt-1 text-[13px] text-[var(--color-text-primary)]">
                {formatPhotoDate(photo.photo_date)}
              </div>
            </div>
          ) : null}

          <div>
            <SectionLabel>Tags</SectionLabel>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {photo.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[var(--color-surface-muted)] px-2.5 py-1 text-[12px] font-semibold text-[var(--color-text-secondary)]"
                >
                  {tag.tag}
                  {tag.source === "AI" ? <Badge tone="blue">AI</Badge> : null}
                  {canManage ? (
                    <button
                      type="button"
                      onClick={() => {
                        setError(null);
                        removeTag.mutate(tag.id, {
                          onError: (mutationError) =>
                            setError(
                              getApiErrorMessage(
                                mutationError,
                                "Couldn't remove this tag. Please try again.",
                              ),
                            ),
                        });
                      }}
                      aria-label={`Remove tag ${tag.tag}`}
                      className="rounded-full text-[var(--color-text-muted)] outline-none transition hover:text-[var(--color-danger)] focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)]"
                    >
                      <Icon name="x" size={9} />
                    </button>
                  ) : null}
                </span>
              ))}
              {photo.tags.length === 0 ? (
                <span className="text-[12px] text-[var(--color-text-muted)]">No tags yet.</span>
              ) : null}
            </div>

            {canManage ? (
              <form onSubmit={submitTag} className="mt-2 flex gap-2">
                <input
                  className={`${inputClass} py-1.5`}
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder="Add a tag"
                />
                <Button
                  type="submit"
                  variant="secondary"
                  size="sm"
                  disabled={!newTag.trim() || addTag.isPending}
                >
                  Add
                </Button>
              </form>
            ) : null}
          </div>
        </div>
      </div>
    </Modal>
  );
}