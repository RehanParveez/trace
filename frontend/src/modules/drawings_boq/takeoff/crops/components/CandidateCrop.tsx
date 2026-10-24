import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../../organizations/components/OrganizationUi";
import type { TakeoffCandidate } from "../../types/takeoff.types";
import { useCandidateCrop } from "../hooks/useCandidateCrop";
import { cropAlt, cropKey, CROP_PX } from "../utils/crops";

interface Props {
  c: Pick<TakeoffCandidate, "id" | "label" | "geometry">;
  pageNo: number;
}

export function CandidateCrop({ c, pageNo }: Props) {
  const { t } = useTranslation();
  const host = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = host.current;
    if (!el || seen) return;
    if (typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const io = new IntersectionObserver((entries) => { if (entries.some((e) => e.isIntersecting)) { setSeen(true); io.disconnect(); } }, { rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  }, [seen]);
  const pic = useCandidateCrop(c.id, cropKey(c), CROP_PX, seen);
  return (
    <div ref={host} className="mt-1.5" data-testid="found-crop">
      {pic.url ? (
        <img src={pic.url} alt={cropAlt(c.label, pageNo)} className="max-h-[260px] w-full max-w-[420px] rounded-[6px] border border-[var(--color-border)] bg-white object-contain" />
      ) : pic.failed ? (
        <div className="text-[11.5px] text-[var(--color-text-muted)]" data-testid="found-crop-failed">
          {t("boq.takeoff.crops.failed", "The picture could not be made. Use Show to find it on the sheet.")}{" "}
          <Button size="sm" variant="ghost" onClick={pic.retry}>{t("boq.takeoff.crops.retry", "Try again")}</Button>
        </div>
      ) : (
        <div className="flex h-[96px] max-w-[420px] items-center justify-center rounded-[6px] border border-dashed border-[var(--color-border)] text-[11.5px] text-[var(--color-text-muted)]">
          {t("boq.takeoff.crops.loading", "Loading the picture…")}
        </div>
      )}
      {pic.url ? <div className="mt-0.5 text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.crops.caption", "Marked in red where it was read on sheet {{n}}.", { n: pageNo })}</div> : null}
    </div>
  );
}
