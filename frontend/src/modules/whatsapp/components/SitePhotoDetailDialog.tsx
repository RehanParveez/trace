import { useState } from "react";
import type { FormEvent } from "react";
import { Badge, Button, Icon, inputClass, Modal, SectionLabel, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import {useAddPhotoTag, useAssignProject, useRemovePhotoTag, useSitePhoto, useUpdateSitePhoto, 
} from "../hooks";
import type { Project } from "../../projects";
import {formatCapturedAt, formatPhoneNumber, formatPhotoDate, getCaptionField,
} from "../utils/whatsapp.utils";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const photoQuery = useSitePhoto(photoId);
  const assignProject = useAssignProject();
  const updatePhoto = useUpdateSitePhoto();
  const addTag = useAddPhotoTag(photoId);
  const removeTag = useRemovePhotoTag(photoId);
  const { showToast } = useToast();

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
        onSuccess: () => {
          setNewTag("");
          showToast({
            tone: "success",
            title: t("whatsapp.photo.tagAddedToast"),
          });
        },
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, t("whatsapp.photo.addTagError"))),
      },
    );
  }

  if (photoQuery.isLoading || !photo) {
    return (
      <Modal title={t("whatsapp.photo.title")} onClose={onClose}>
        <div className="py-8 text-center text-[12.5px] text-[var(--color-text-secondary)]">
          {t("common.loading")}
        </div>
      </Modal>
    );
  }
  const location = locationDraft ?? photo.location_text ?? "";
  const photoDate = dateDraft ?? photo.photo_date ?? "";
  const noteText = getCaptionField(photo.caption_parsed, "notes");

  return (
    <Modal
      title={t("whatsapp.photo.title")}
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
            <SectionLabel>{t("whatsapp.photo.sender")}</SectionLabel>
            <div className="mt-1 text-[13.5px] font-semibold text-[var(--color-text-primary)]">
              {formatPhoneNumber(photo.sender_phone_number)}
            </div>
          </div>

          {photo.caption_raw ? (
            <div>
              <SectionLabel>{t("whatsapp.photo.caption")}</SectionLabel>
              <div className="mt-1 text-[13px] leading-5 text-[var(--color-text-primary)]">
                {photo.caption_raw}
              </div>
              {noteText ? (
                <div className="mt-1 text-[12px] italic text-[var(--color-text-secondary)]">
                  {t("whatsapp.photo.aiNotes")}: {noteText}
                </div>
              ) : null}
            </div>
          ) : null}

          <div>
            <SectionLabel>{t("whatsapp.photo.project")}</SectionLabel>
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
                      onSuccess: () =>
                        showToast({
                          tone: "success",
                          title: t("whatsapp.photo.assignedToast"),
                        }),
                      onError: (mutationError) =>
                        setError(
                          getApiErrorMessage(
                            mutationError,
                            t("whatsapp.photo.assignError"),
                          ),
                        ),
                    },
                  );
                }}
              >
                <option value="" disabled>
                 {t("whatsapp.photo.selectProject")}
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
              <SectionLabel>{t("whatsapp.photo.location")}</SectionLabel>
              <div className="mt-1.5 flex gap-2">
                <input
                  className={inputClass}
                  value={location}
                  onChange={(e) => setLocationDraft(e.target.value)}
                  placeholder={t("whatsapp.photo.locationPlaceholder")}
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
                        onSuccess: () => {
                          setLocationDraft(null);
                          showToast({
                            tone: "success",
                            title: t("whatsapp.photo.locationUpdatedToast"),
                          });
                        },
                        onError: (mutationError) =>
                          setError(
                            getApiErrorMessage(
                              mutationError,
                              t("whatsapp.photo.locationError"),
                            ),
                          ),
                      },
                    );
                  }}
                >
                  {t("common.save")}
                </Button>
              </div>
            </div>
          ) : photo.location_text ? (
            <div>
              <SectionLabel>{t("whatsapp.photo.location")}</SectionLabel>
              <div className="mt-1 text-[13px] text-[var(--color-text-primary)]">
                {photo.location_text}
              </div>
            </div>
          ) : null}

          {canManage ? (
            <div>
              <SectionLabel>{t("whatsapp.photo.capturedDate")}</SectionLabel>
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
                        onSuccess: () => {
                          setDateDraft(null);
                          showToast({
                            tone: "success",
                            title: t("whatsapp.photo.dateUpdatedToast"),
                          });
                        },
                        onError: (mutationError) =>
                          setError(
                            getApiErrorMessage(
                              mutationError,
                              t("whatsapp.photo.dateError"),
                            ),
                          ),
                      },
                    );
                  }}
                >
                  {t("whatsapp.photo.tags")}
                </Button>
              </div>
            </div>
          ) : photo.photo_date ? (
            <div>
              <SectionLabel>{t("whatsapp.photo.capturedDate")}</SectionLabel>
              <div className="mt-1 text-[13px] text-[var(--color-text-primary)]">
                {formatPhotoDate(photo.photo_date)}
              </div>
            </div>
          ) : null}

          <div>
            <SectionLabel>{t("whatsapp.photo.tags")}</SectionLabel>
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
                          onSuccess: () =>
                            showToast({
                              tone: "success",
                              title: t("whatsapp.photo.tagRemovedToast"),
                            }),
                          onError: (mutationError) =>
                            setError(
                              getApiErrorMessage(
                                mutationError,
                                t("whatsapp.photo.removeTagError"),
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
                <span className="text-[12px] text-[var(--color-text-muted)]">{t("whatsapp.photo.noTags")}</span>
              ) : null}
            </div>

            {canManage ? (
              <form onSubmit={submitTag} className="mt-2 flex gap-2">
                <input
                  className={`${inputClass} py-1.5`}
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder={t("whatsapp.photo.addTagPlaceholder")}
                />
                <Button
                  type="submit"
                  variant="secondary"
                  size="sm"
                  disabled={!newTag.trim() || addTag.isPending}
                >
                  {t("whatsapp.photo.addTag")}
                </Button>
              </form>
            ) : null}
          </div>
        </div>
      </div>
    </Modal>
  );
}