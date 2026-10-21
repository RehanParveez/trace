import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { readingGapsResponse } from "../types/readingGaps.types";
import { ASIDE_REASON_TEXT, LEFT_OUT_COLOUR, TAG_REASON_TEXT, leftOutCounts, leftOutNote } from "../utils/readingGaps";

interface Props {
  on: boolean;
  onToggle: (on: boolean) => void;
  data: readingGapsResponse | undefined;
  loading: boolean;
  error: unknown;
}

function Dot({ colour }: { colour: string }) {
  return <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colour }} />;
}

export function LeftOutBar({ on, onToggle, data, loading, error }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const counts = leftOutCounts(data);
  const note = on ? leftOutNote({ loading, error, data }) : null;
  return (
    <div className="border-b border-[var(--color-border)] px-4 py-1 text-[11.5px] text-[var(--color-text-secondary)]" data-testid="left-out" data-on={on}>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={on} onChange={(e) => onToggle(e.target.checked)} data-testid="left-out-toggle" />
          <span className="font-semibold">{t("boq.takeoff.leftOut.title", "Show what the reader left out")}</span>
        </label>
        {on && counts.read ? (
          counts.empty ? (
            <span data-testid="left-out-none">{t("boq.takeoff.leftOut.none", "Nothing left out on this sheet.")}</span>
          ) : (
            <span className="flex flex-wrap items-center gap-3" data-testid="left-out-counts">
              <span className="inline-flex items-center gap-1"><Dot colour={LEFT_OUT_COLOUR.NO_MEMBER} />{t("boq.takeoff.leftOut.noMember", { defaultValue: "{{count}} mark(s) with a known kind but no member", count: counts.noMember })}</span>
              <span className="inline-flex items-center gap-1"><Dot colour={LEFT_OUT_COLOUR.UNKNOWN_KIND} />{t("boq.takeoff.leftOut.unknown", { defaultValue: "{{count}} mark(s) of unknown kind", count: counts.unknownKind })}</span>
              <span className="inline-flex items-center gap-1"><Dot colour={LEFT_OUT_COLOUR.INVALID} />{t("boq.takeoff.leftOut.setAside", { defaultValue: "{{count}} item(s) set aside", count: counts.setAside })}</span>
              <button type="button" className="underline" onClick={() => setOpen((v) => !v)} data-testid="left-out-list-toggle">
                {open ? t("boq.takeoff.leftOut.hide", "Hide list") : t("boq.takeoff.leftOut.show", "Show list")}
              </button>
            </span>
          )
        ) : null}
        {note ? <span data-testid="left-out-note">{t("boq.takeoff.leftOut.note", note)}</span> : null}
      </div>
      {on && open && counts.read && !counts.empty ? (
        <div className="mt-1 max-h-40 overflow-auto rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-2" data-testid="left-out-list">
          <ul className="space-y-0.5">
            {(data?.tags ?? []).map((tag) => (
              <li key={`t-${tag.tag}`} className="flex items-center gap-2" data-testid="left-out-tag">
                <Dot colour={LEFT_OUT_COLOUR[tag.reason]} />
                <span className="font-mono font-semibold">{tag.tag}</span>
                <span>×{tag.count}</span>
                <span className="text-[var(--color-text-muted)]">{TAG_REASON_TEXT[tag.reason]}</span>
              </li>
            ))}
            {(data?.set_aside ?? []).map((item) => (
              <li key={`a-${item.id}`} className="flex items-center gap-2" data-testid="left-out-aside">
                <Dot colour={LEFT_OUT_COLOUR[item.reason]} />
                <span className="font-mono font-semibold">{item.tag || item.label || "item"}</span>
                <span className="text-[var(--color-text-muted)]">{ASIDE_REASON_TEXT[item.reason]}{item.codes.length ? `: ${item.codes.join(", ")}` : ""}</span>
              </li>
            ))}
          </ul>
          {counts.cut > 0 ? <div className="mt-1 text-[var(--color-text-muted)]">{t("boq.takeoff.leftOut.cut", { defaultValue: "{{count}} more are not listed.", count: counts.cut })}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
