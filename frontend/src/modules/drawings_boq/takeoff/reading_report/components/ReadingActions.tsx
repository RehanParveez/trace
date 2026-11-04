import { useState } from "react";
import type { Box, MisreadKind, ReportItem } from "../types/readingReport.types";
import { CLASS_CHOICES, classText, MISREAD_TEXT } from "../utils/readingReport";

const FIELD = "w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-[12px]";
const BTN = "rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[11.5px] disabled:opacity-50";

interface MarkProps {
  box: Box | null;
  busy: boolean;
  initialClass?: string;
  onChooseArea: () => void;
  onSubmit: (v: { item_class: string; mark: string; note: string; attrs: Record<string, string> }) => void;
  onCancel: () => void;
}

export function MarkManuallyForm({ box, busy, initialClass = "COLUMN", onChooseArea, onSubmit, onCancel }: MarkProps) {
  const [cls, setCls] = useState(initialClass);
  const [mark, setMark] = useState("");
  const [size, setSize] = useState("");
  const [note, setNote] = useState("");
  return (
    <form
      className="space-y-2 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12px]"
      data-testid="mark-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (box) onSubmit({ item_class: cls, mark: mark.trim(), note: note.trim(), attrs: size.trim() ? { size: size.trim() } : {} });
      }}
    >
      <h3 className="font-semibold">Mark manually</h3>
      <p className="text-[11.5px] text-[var(--color-text-secondary)]">Use this when the reader missed something. The mark is used for this project only. It is not counted as a correct reading until someone checks it against the sheet.</p>
      <label className="block">Kind<select className={FIELD} value={cls} onChange={(e) => setCls(e.target.value)}>{CLASS_CHOICES.map((c) => <option key={c} value={c}>{classText(c)}</option>)}</select></label>
      <label className="block">Mark<input className={FIELD} value={mark} maxLength={60} onChange={(e) => setMark(e.target.value)} placeholder="C-6" /></label>
      <label className="block">Size or value as printed<input className={FIELD} value={size} maxLength={60} onChange={(e) => setSize(e.target.value)} placeholder="9×18 in" /></label>
      <label className="block">Note<textarea className={FIELD} value={note} maxLength={2000} rows={2} onChange={(e) => setNote(e.target.value)} /></label>
      <div className="flex items-center gap-2">
        <button type="button" className={BTN} onClick={onChooseArea} data-testid="choose-area">{box ? "Choose the area again" : "Choose the area on the sheet"}</button>
        {box ? <span className="text-[11px] text-[var(--color-text-muted)]">area chosen</span> : <span className="text-[11px] text-[var(--color-warning)]">no area yet</span>}
      </div>
      <div className="flex gap-2">
        <button type="submit" className={BTN} disabled={busy || !box} data-testid="mark-save">Save mark</button>
        <button type="button" className={BTN} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

interface MisreadProps {
  item: ReportItem | null;
  box: Box | null;
  busy: boolean;
  onChooseArea: () => void;
  onSubmit: (v: { kind: MisreadKind; expected: string; note: string }) => void;
  onCancel: () => void;
}

export function MisreadForm({ item, box, busy, onChooseArea, onSubmit, onCancel }: MisreadProps) {
  const [kind, setKind] = useState<MisreadKind>(item ? "WRONG_VALUE" : "MISSED");
  const [expected, setExpected] = useState("");
  const [note, setNote] = useState("");
  const needsPlace = !item && !box;
  return (
    <form
      className="space-y-2 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12px]"
      data-testid="misread-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (!needsPlace) onSubmit({ kind, expected: expected.trim(), note: note.trim() });
      }}
    >
      <h3 className="font-semibold">Report misread</h3>
      <p className="text-[11.5px] text-[var(--color-text-secondary)]">{item ? `About ${item.mark ? `${classText(item.class)} ${item.mark}` : item.label}.` : "About an area of the sheet."} The report goes to the people who check the reader against the drawings.</p>
      <label className="block">What is wrong<select className={FIELD} value={kind} onChange={(e) => setKind(e.target.value as MisreadKind)}>{(Object.keys(MISREAD_TEXT) as MisreadKind[]).map((k) => <option key={k} value={k}>{MISREAD_TEXT[k]}</option>)}</select></label>
      <label className="block">What it should be<input className={FIELD} value={expected} maxLength={200} onChange={(e) => setExpected(e.target.value)} placeholder="e.g. 9×18 in, or: a door D2" /></label>
      <label className="block">Note<textarea className={FIELD} value={note} maxLength={2000} rows={2} onChange={(e) => setNote(e.target.value)} /></label>
      {item ? null : (
        <div className="flex items-center gap-2">
          <button type="button" className={BTN} onClick={onChooseArea} data-testid="choose-area">{box ? "Choose the area again" : "Choose the area on the sheet"}</button>
          {box ? <span className="text-[11px] text-[var(--color-text-muted)]">area chosen</span> : <span className="text-[11px] text-[var(--color-warning)]">no area yet</span>}
        </div>
      )}
      <div className="flex gap-2">
        <button type="submit" className={BTN} disabled={busy || needsPlace} data-testid="misread-save">Send report</button>
        <button type="button" className={BTN} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
