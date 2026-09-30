import { useState, useRef } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button, EmptyState, ErrorState, LoadingState, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useProjects } from "../../projects";
import { useSitePhotos, useUploadSitePhoto } from "../hooks";
import type { SitePhotoListParams } from "../types/whatsapp.types";
import { SitePhotoCard } from "./SitePhotoCard";
import { SitePhotoDetailDialog } from "./SitePhotoDetailDialog";
import { useTranslation } from "react-i18next";

interface SitePhotoGalleryProps {
  projectId?: string;
  canManage: boolean;
}

export function SitePhotoGallery({ projectId, canManage }: SitePhotoGalleryProps) {
  const { t } = useTranslation();
  const [tagFilter, setTagFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [unassignedOnly, setUnassignedOnly] = useState(false);
  const [viewingPhotoId, setViewingPhotoId] = useState<string | null>(null);

  const [uploadProjectId, setUploadProjectId] = useState(projectId ?? "");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const uploadPhoto = useUploadSitePhoto();
  const { showToast } = useToast();

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

  function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const selectedProjectId = projectId ?? uploadProjectId;

    if (!selectedProjectId || !uploadFile) {
     return;
    }

    setUploadError(null);

    uploadPhoto.mutate(
     {
       projectId: selectedProjectId,
       file: uploadFile,
     },
     {
       onSuccess: () => {
        setUploadFile(null);

        if (uploadInputRef.current) {
          uploadInputRef.current.value = "";
        }

        showToast({
          tone: "success",
          title: t("whatsapp.gallery.uploadSuccess"),
        });
      },
       onError: (error) => {
        setUploadError(
          getApiErrorMessage(
            error,
            t("whatsapp.gallery.uploadError"),
          ),
        );
      },
    },
  );
}

  return (
    <div className="space-y-4">
      {canManage ? (
       <form
          onSubmit={handleUpload}
          className="flex flex-wrap items-end gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3"
       >
          {!projectId ? (
            <label className="flex min-w-[220px] flex-1 flex-col gap-1.5 text-[12px] font-medium text-[var(--color-text-secondary)]">
              {t("whatsapp.gallery.uploadProject")}
              <select
                required
                value={uploadProjectId}
                onChange={(event) => setUploadProjectId(event.target.value)}
                className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-2 text-[13px] text-[var(--color-text-primary)]"
              >
                <option value="">
                  {t("whatsapp.gallery.selectProject")}
                </option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

         <label className="flex min-w-[220px] flex-1 flex-col gap-1.5 text-[12px] font-medium text-[var(--color-text-secondary)]">
           {t("whatsapp.gallery.uploadFile")}
           <input
             ref={uploadInputRef}
             type="file"
             accept="image/jpeg,image/png,image/webp"
             required
             onChange={(event) => {
              setUploadError(null);
              setUploadFile(event.currentTarget.files?.[0] ?? null);
           }}
             className="text-[12px] text-[var(--color-text-secondary)] file:mr-3 file:rounded-[7px] file:border file:border-[var(--color-border)] file:bg-[var(--color-surface)] file:px-3 file:py-2 file:text-[12px] file:font-semibold"
            />
         </label>

        <Button
          type="submit"
          variant="primary"
          disabled={
            !(projectId ?? uploadProjectId) ||
            !uploadFile ||
            uploadPhoto.isPending
          }
        >
        {uploadPhoto.isPending
          ? t("whatsapp.gallery.uploading")
          : t("whatsapp.gallery.upload")}
        </Button>

        {uploadError ? (
         <p
           role="alert"
           className="w-full text-[12px] text-[var(--color-danger)]"
         >
          {uploadError}
         </p>
        ) : null}
      </form>
     ) : null}
      <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <input
          className="w-[160px] rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12.5px] outline-none focus-visible:border-[var(--color-trace-gold-dark)]"
          placeholder={t("whatsapp.gallery.filterTag")}
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          aria-label={t("whatsapp.gallery.filterTagAria")}
        />
        <input
          type="date"
          className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px] outline-none focus-visible:border-[var(--color-trace-gold-dark)]"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          aria-label={t("whatsapp.gallery.filterFromAria")}
        />
        <span className="text-[12px] text-[var(--color-text-muted)]">{t("whatsapp.gallery.to")}</span>
        <input
          type="date"
          className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px] outline-none focus-visible:border-[var(--color-trace-gold-dark)]"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          aria-label={t("whatsapp.gallery.filterToAria")}
        />
        <label className="ml-auto flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={unassignedOnly} onChange={(e) => setUnassignedOnly(e.target.checked)} className="accent-[var(--color-trace-gold)]" />
          {t("whatsapp.gallery.needsProjectOnly")}
        </label>
      </div>

      {photosQuery.isLoading ? (
        <LoadingState label={t("whatsapp.gallery.loading")} />
      ) : photosQuery.isError ? (
        <ErrorState title={t("whatsapp.gallery.loadError")} onRetry={() => void photosQuery.refetch()} />
      ) : (photosQuery.data ?? []).length === 0 ? (
        <EmptyState
          icon="site"
          title={t("whatsapp.gallery.emptyTitle")}
          description={t("whatsapp.gallery.emptyDesc")}
          action={
            <Link to="/app/whatsapp-settings">
              <Button variant="primary" size="sm">
                {t("whatsapp.gallery.checkConnection")}
              </Button>
            </Link>
          }
        />
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