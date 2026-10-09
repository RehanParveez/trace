import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEventHandler } from "react";
import { useTranslation } from "react-i18next";
import { apiClient } from "../api/client";
import { getApiErrorCode } from "../../modules/identity";

type Props = {
  photoId?: string | null;
  src?: string | null;
  alt: string;
  className?: string;
  loading?: "lazy" | "eager";
  onClick?: MouseEventHandler<HTMLElement>;
};

type Phase = "loading" | "ready" | "refreshing" | "missing" | "failed";

type FreshUrl = { photo_url: string };

async function fetchFreshUrl(photoId: string): Promise<string> {
  const response = await apiClient.get<FreshUrl>(`/whatsapp/photos/${photoId}/url`);
  return response.data.photo_url;
}

export function SitePhotoImage({ photoId, src, alt, className = "", loading = "lazy", onClick }: Props) {
  const { t } = useTranslation();
  const [currentSrc, setCurrentSrc] = useState<string | null>(src ?? null);
  const [phase, setPhase] = useState<Phase>(src ? "loading" : "refreshing");
  const [propSrc, setPropSrc] = useState<string | null>(src ?? null);
  const refreshedFor = useRef<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  if ((src ?? null) !== propSrc) {
    setPropSrc(src ?? null);
    setCurrentSrc(src ?? null);
    setPhase(src ? "loading" : "refreshing");
    refreshedFor.current = null;
  }

  const refresh = useCallback(async () => {
    if (!photoId) {
      setPhase("failed");
      return;
    }
    setPhase("refreshing");
    try {
      const fresh = await fetchFreshUrl(photoId);
      if (!mounted.current) return;
      refreshedFor.current = fresh;
      setCurrentSrc(fresh);
      setPhase("loading");
    } catch (error) {
      if (!mounted.current) return;
      setPhase(getApiErrorCode(error) === "SITE_PHOTO_FILE_MISSING" ? "missing" : "failed");
    }
  }, [photoId]);

  useEffect(() => {
    if (!currentSrc && photoId && phase === "refreshing") void refresh();
  }, [currentSrc, photoId, phase, refresh]);

  const handleError = () => {
    if (currentSrc && refreshedFor.current === currentSrc) {
      setPhase("failed");
      return;
    }
    void refresh();
  };

  if (phase === "missing" || phase === "failed" || (!currentSrc && phase !== "refreshing")) {
    const missing = phase === "missing";
    return (
      <div
        role="img"
        aria-label={alt}
        onClick={onClick}
        className={`flex flex-col items-center justify-center gap-1 bg-[var(--color-surface-muted)] p-2 text-center text-[11px] text-[var(--color-text-secondary)] ${className}`}
      >
        <span>
          {missing
            ? t("sitePhoto.missing", { defaultValue: "Image file not found" })
            : t("sitePhoto.unavailable", { defaultValue: "Image unavailable" })}
        </span>
        {!missing && photoId ? (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              refreshedFor.current = null;
              void refresh();
            }}
            className="rounded-[6px] border border-[var(--color-border)] px-2 py-0.5 font-semibold hover:bg-[var(--color-surface)]"
          >
            {t("sitePhoto.retry", { defaultValue: "Try again" })}
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className={`relative overflow-hidden ${className}`} onClick={onClick}>
      {currentSrc ? (
        <img
          src={currentSrc}
          alt={alt}
          loading={loading}
          onLoad={() => setPhase("ready")}
          onError={handleError}
          className={`h-full w-full object-cover transition-opacity ${phase === "ready" ? "opacity-100" : "opacity-0"}`}
        />
      ) : null}
      {phase !== "ready" ? (
        <div aria-hidden className="absolute inset-0 animate-pulse bg-[var(--color-surface-muted)]" />
      ) : null}
    </div>
  );
}
