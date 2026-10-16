import { useTranslation } from "react-i18next";
import type { DrawingFacts } from "../types/takeoff.types";
import { beamRows, beamText, hasPictureReads, pictureReaderMissing, pictureSource, sourceLabel, tankRows, tankSizeText, tankSizes } from "../utils/pictures";

interface Props {
  facts: DrawingFacts | undefined;
}

export function PictureReadsSection({ facts }: Props) {
  const { t } = useTranslation();
  if (!hasPictureReads(facts)) return null;
  const beams = beamRows(facts);
  const tanks = tankRows(facts);
  const missing = pictureReaderMissing(facts);
  return (
    <details data-testid="picture-reads">
      <summary className="cursor-pointer text-[11px] text-[var(--color-text-muted)]">
        {t("drawings.pictures.summary", { defaultValue: "{{b}} beam sections and {{k}} tank drawings read from the structural sheet", b: beams.length, k: tanks.length })}
      </summary>
      {missing ? (
        <p className="mt-1 text-[11px] text-[var(--color-warning)]" data-testid="picture-reader-missing">
          {t("drawings.pictures.readerMissing", "The character reader is not installed on the server, so values that are drawn as pictures were not read. Type the beam depths and tank heights, or ask for the reader (tesseract) to be installed.")}
        </p>
      ) : null}
      <ul className="mt-1 list-none space-y-0.5 pl-0 text-[var(--color-text-muted)]">
        {beams.map((d, i) => {
          const src = pictureSource(d.read);
          const text = beamText(d);
          return (
            <li key={`b-${d.mark}-${d.page_no}-${i}`} data-testid={`beam-read-${d.mark}`}>
              <span className="font-semibold text-[var(--color-text-primary)]">{d.mark}</span>
              {text ? ` · ${text}` : ` · ${t("drawings.pictures.noValue", "no depth or bars read")}`}
              {` · ${t(`drawings.pictures.source.${src}`, sourceLabel(src))}`}
              {d.page_no ? ` · ${t("drawings.checks.page", { defaultValue: "page {{p}}", p: d.page_no })}` : ""}
            </li>
          );
        })}
        {tanks.map((d, i) => {
          const src = pictureSource(d.read);
          const sizes = tankSizes(d).map(tankSizeText).join(", ");
          return (
            <li key={`t-${d.kind}-${d.view}-${d.page_no}-${i}`} data-testid={`tank-read-${d.kind}-${d.view}`}>
              <span className="font-semibold text-[var(--color-text-primary)]">{`${d.kind ?? "TANK"} ${String(d.view ?? "").toLowerCase()}`}</span>
              {sizes ? ` · ${sizes}` : ` · ${t("drawings.pictures.noSize", "no size read")}`}
              {d.bar_notes.length ? ` · ${t("drawings.pictures.barNotes", { defaultValue: "{{n}} bar notes (text)", n: d.bar_notes.length })}` : ""}
              {` · ${t(`drawings.pictures.source.${src}`, sourceLabel(src))}`}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
