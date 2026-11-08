import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { aiShadowApi } from "../../ai_reader/api/aiShadow.api";
import { CandidateCrop } from "../../crops/components/CandidateCrop";
import type { ReviewRow } from "../types/review.types";

const CANDIDATE = /^\/takeoff\/candidates\/([^/]+)\/crop$/;
const SHADOW = /^\/takeoff\/ai-shadow\/([^/]+)\/crop$/;

function ShadowCrop({ readId, alt }: { readId: string; alt: string }) {
  const { t } = useTranslation();
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let made: string | null = null;
    let alive = true;
    setUrl(null);
    setFailed(false);
    aiShadowApi.crop(readId).then((blob) => {
      if (!alive) return;
      made = URL.createObjectURL(blob);
      setUrl(made);
    }).catch(() => alive && setFailed(true));
    return () => {
      alive = false;
      if (made) URL.revokeObjectURL(made);
    };
  }, [readId]);
  if (failed) return <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.review.cropFailed", "The picture could not be loaded.")}</p>;
  if (!url) return <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.review.cropLoading", "Loading the picture…")}</p>;
  return <img src={url} alt={alt} className="max-h-[320px] w-full rounded-[6px] border border-[var(--color-border)] bg-white object-contain" />;
}

export function ReviewCrop({ row }: { row: ReviewRow }) {
  const { t } = useTranslation();
  const candidate = row.crop_url ? CANDIDATE.exec(row.crop_url) : null;
  const shadow = row.crop_url ? SHADOW.exec(row.crop_url) : null;
  if (candidate) return <CandidateCrop c={{ id: candidate[1], label: row.item, geometry: { points: [] } }} pageNo={row.page ?? 0} />;
  if (shadow) return <ShadowCrop readId={shadow[1]} alt={`${row.item} (sheet ${row.page ?? ""})`} />;
  return <p className="text-[11.5px] text-[var(--color-text-muted)]">{t("boq.review.noCrop", "No picture of the sheet is kept for this row.")}</p>;
}
