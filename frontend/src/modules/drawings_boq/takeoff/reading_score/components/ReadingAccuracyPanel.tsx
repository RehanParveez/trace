import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, useToast } from "../../../../organizations/components/OrganizationUi";
import {useDeriveLabels, useImportLabels, useLabelTemplate, useReadingLabels, useReadingScore, useReadingScores, useRunReadingScore, useScoreComparison,
} from "../hooks/useReadingScore";
import type { ScoreComparison, ScoreDetail, ScoreListItem, ScoreMode } from "../types/readingScore.types";
import { takeoffErrorMessage } from "../../utils/errors";
import {baselineLine, deltaTone, familyName, familyRows, headline, importFormatOf, labelsLine, memberText, notJudgedLine, pointsDelta, regressionLines, rulePairs, runBlocked, runBody,
  sheetBasisText, statusLabel, statusTone, toggleCompare, versionLabel, WHY_TEXT,
} from "../utils/readingScore";

interface Props {
  drawingId: string;
  canEdit: boolean;
}

const BTN = "rounded-[8px] border border-[var(--color-border)] px-2 py-1 text-[11.5px] disabled:opacity-50";
const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";
const TONE_CLASS = { good: "text-[var(--color-success,#067647)]", bad: "text-[var(--color-danger,#b42318)]", same: "text-[var(--color-text-muted)]", none: "text-[var(--color-text-muted)]" } as const;

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function ScoreView({ detail }: { detail: ScoreDetail }) {
  const { t } = useTranslation();
  const r = detail.result;
  const rows = familyRows(r.families);
  const reasons = regressionLines(detail.baseline);
  const line = baselineLine(detail.baseline);
  return (
    <div className="mt-2 space-y-2" data-testid="score-detail">
      <p className="font-semibold" data-testid="score-headline">{headline(r.totals)}</p>
      <p className={MUTED}>{versionLabel(detail)}</p>
      {line ? <p className={MUTED} data-testid="score-baseline">{line}</p> : null}
      {reasons.length ? <ul className="list-disc pl-4 text-[11.5px] text-[var(--color-danger,#b42318)]" data-testid="score-regression">{reasons.map((x) => <li key={x}>{x}</li>)}</ul> : null}
      <p className={MUTED} data-testid="score-rule">{t("boq.takeoff.accuracy.rule", "Match rule used") + ": " + rulePairs(r.rule).join(" · ")}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[11.5px]" data-testid="score-families">
          <thead>
            <tr className="text-[var(--color-text-secondary)]">
              <th className="pr-2">{t("boq.takeoff.accuracy.kind", "Kind")}</th>
              <th className="pr-2">{t("boq.takeoff.accuracy.labelled", "Labelled")}</th>
              <th className="pr-2">{t("boq.takeoff.accuracy.right", "Found right")}</th>
              <th className="pr-2">{t("boq.takeoff.accuracy.missed", "Missed")}</th>
              <th className="pr-2">{t("boq.takeoff.accuracy.wrong", "Wrong")}</th>
              <th className="pr-2">{t("boq.takeoff.accuracy.precision", "Precision")}</th>
              <th className="pr-2">{t("boq.takeoff.accuracy.recall", "Recall")}</th>
              <th>{t("boq.takeoff.accuracy.size", "Size right")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.family} data-testid={`score-family-${f.family}`}>
                <td className="pr-2 font-medium">{f.name}</td>
                <td className="pr-2">{f.labels}</td>
                <td className="pr-2">{f.right}</td>
                <td className="pr-2">{f.missed}</td>
                <td className="pr-2">{f.wrong}{f.unlabelled ? <span className="text-[var(--color-text-muted)]">{` (+${f.unlabelled} not labelled)`}</span> : null}</td>
                <td className="pr-2">{f.precision}</td>
                <td className="pr-2">{f.recall}</td>
                <td>{f.size}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.some((f) => f.upperBound) ? (
        <p className={MUTED}>{t("boq.takeoff.accuracy.upperBound", "≤ means precision can be no higher than shown: some sheets are only partly labelled, so reads that match no label are not counted wrong.")}</p>
      ) : null}
      {r.could_not_judge.length ? (
        <div data-testid="score-not-judged">
          <p className="font-semibold">{t("boq.takeoff.accuracy.notJudged", "Could not judge")}</p>
          <ul className="list-disc pl-4 text-[11.5px]">{r.could_not_judge.map((c) => <li key={`${c.page_no}-${c.reason}`}>{notJudgedLine(c)}</li>)}</ul>
        </div>
      ) : null}
      {r.sheets.map((s) => (
        <details key={s.sheet_id} className="rounded-[8px] border border-[var(--color-border)] p-2" data-testid={`score-sheet-${s.page_no}`}>
          <summary className="cursor-pointer">
            <span className="font-medium">{`Sheet ${s.page_no}${s.title ? ` (${s.title})` : ""}`}</span>
            <span className={`ml-2 ${MUTED}`}>{`${s.misses.length + s.misses_cut} missed · ${s.wrong.length + s.wrong_cut} wrong`}</span>
          </summary>
          <p className={`mt-1 ${MUTED}`}>{sheetBasisText(s.basis)}</p>
          {s.misses.length ? (
            <div className="mt-1">
              <p className="font-medium">{t("boq.takeoff.accuracy.missedList", "Missed")}</p>
              <ul className="list-disc pl-4 text-[11.5px]">
                {s.misses.map((m, i) => <li key={`m${i}`}>{`${familyName(m.family)} ${memberText(m)} — ${WHY_TEXT[m.why] ?? m.why}`}</li>)}
              </ul>
              {s.misses_cut ? <p className={MUTED}>{`+${s.misses_cut} more not listed`}</p> : null}
            </div>
          ) : null}
          {s.wrong.length ? (
            <div className="mt-1">
              <p className="font-medium">{t("boq.takeoff.accuracy.wrongList", "Wrong")}</p>
              <ul className="list-disc pl-4 text-[11.5px]">
                {s.wrong.map((m, i) => <li key={`w${i}`}>{`${familyName(m.family)} ${memberText(m)} — ${WHY_TEXT[m.why] ?? m.why}`}</li>)}
              </ul>
              {s.wrong_cut ? <p className={MUTED}>{`+${s.wrong_cut} more not listed`}</p> : null}
            </div>
          ) : null}
        </details>
      ))}
    </div>
  );
}

function CompareView({ cmp }: { cmp: ScoreComparison }) {
  const { t } = useTranslation();
  const d = cmp.d_totals;
  return (
    <div className="mt-2 space-y-1.5" data-testid="score-compare">
      {!cmp.same_rule || !cmp.same_mode ? (
        <p className="text-[11.5px] text-[var(--color-danger,#b42318)]">{t("boq.takeoff.accuracy.notSame", "These two scores used a different match rule or mode, so the change is not a like-for-like comparison.")}</p>
      ) : null}
      <p className="font-semibold">
        {[["F1", d.f1], ["recall", d.recall], ["precision", d.precision]].map(([name, v]) => (
          <span key={String(name)} className={`mr-3 ${TONE_CLASS[deltaTone(v as number | null)]}`}>{`${name} ${pointsDelta(v as number | null)}`}</span>
        ))}
      </p>
      <ul className="text-[11.5px]">
        {cmp.families.map((f) => (
          <li key={f.family} className="flex gap-2">
            <span className="w-28">{familyName(f.family)}</span>
            <span className={TONE_CLASS[deltaTone(f.d_f1)]}>{`F1 ${pointsDelta(f.d_f1)}`}</span>
            <span className={TONE_CLASS[deltaTone(f.d_recall)]}>{`recall ${pointsDelta(f.d_recall)}`}</span>
            <span className={TONE_CLASS[deltaTone(f.d_precision)]}>{`precision ${pointsDelta(f.d_precision)}`}</span>
          </li>
        ))}
      </ul>
      {cmp.lost.length ? (
        <div>
          <p className="font-medium">{t("boq.takeoff.accuracy.lost", "Found before, not found now")}</p>
          <ul className="list-disc pl-4 text-[11.5px]">{cmp.lost.map((m, i) => <li key={`l${i}`}>{`Sheet ${m.page_no}: ${familyName(m.family)} ${memberText(m)}`}</li>)}</ul>
        </div>
      ) : null}
      {cmp.gained.length ? (
        <div>
          <p className="font-medium">{t("boq.takeoff.accuracy.gained", "Not found before, found now")}</p>
          <ul className="list-disc pl-4 text-[11.5px]">{cmp.gained.map((m, i) => <li key={`g${i}`}>{`Sheet ${m.page_no}: ${familyName(m.family)} ${memberText(m)}`}</li>)}</ul>
        </div>
      ) : null}
    </div>
  );
}

function ScoreRow({ s, selected, open, onOpen, onPick }: { s: ScoreListItem; selected: boolean; open: boolean; onOpen: () => void; onPick: () => void }) {
  return (
    <li className="flex flex-wrap items-center gap-2" data-testid={`score-row-${s.id}`}>
      <input type="checkbox" checked={selected} onChange={onPick} aria-label="Compare" />
      <Badge tone={statusTone(s.status)}>{statusLabel(s.status)}</Badge>
      <button type="button" className="underline" onClick={onOpen} aria-expanded={open}>{headline(s.totals)}</button>
      <span className={MUTED}>{`${versionLabel(s)} · ${when(s.created_at)}`}</span>
      {s.partial ? <Badge tone="gold">Partial</Badge> : null}
      {s.note ? <span className={MUTED}>{s.note}</span> : null}
    </li>
  );
}

export function ReadingAccuracyPanel({ drawingId, canEdit }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<ScoreMode>("DRY_RUN");
  const [marksOnly, setMarksOnly] = useState(false);
  const [labelDrawingId, setLabelDrawingId] = useState("");
  const [note, setNote] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importFormat, setImportFormat] = useState<"CSV" | "JSON">("CSV");
  const [replace, setReplace] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  const [shown, setShown] = useState<string | null>(null);

  const labels = useReadingLabels(drawingId, open);
  const scores = useReadingScores(drawingId, open);
  const template = useLabelTemplate(open && importOpen);
  const shownScore = useReadingScore(shown);
  const [a, b] = picked;
  const cmp = useScoreComparison(drawingId, a ?? null, b ?? null);
  const derive = useDeriveLabels(drawingId);
  const importer = useImportLabels(drawingId);
  const run = useRunReadingScore(drawingId);

  const options = { mode, marksOnly, labelDrawingId, note };
  const blocked = runBlocked(options, labels.data);
  const fail = (title: string) => (e: unknown) => showToast({ tone: "error", title, description: takeoffErrorMessage(e) });

  const onDerive = () =>
    derive.mutate(undefined, {
      onSuccess: (r) => showToast({ tone: "success", title: t("boq.takeoff.accuracy.derived", "Labels made from the register"), description: `${r.added} added · ${r.updated} changed · ${r.revoked} withdrawn` }),
      onError: fail(t("boq.takeoff.accuracy.deriveError", "Could not make the labels")),
    });

  const onImport = () =>
    importer.mutate({ format: importFormat, content: importText, replace_imported: replace }, {
      onSuccess: (r) => { setImportText(""); setImportOpen(false); showToast({ tone: "success", title: t("boq.takeoff.accuracy.imported", "Ground truth imported"), description: `${r.added} labels on ${r.sheets} sheet${r.sheets === 1 ? "" : "s"}` }); },
      onError: fail(t("boq.takeoff.accuracy.importError", "Could not import the file")),
    });

  const onRun = () =>
    run.mutate(runBody(options), {
      onSuccess: (r) => { setShown(r.id); },
      onError: fail(t("boq.takeoff.accuracy.runError", "Could not score the reader")),
    });

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    const fmt = importFormatOf(file.name);
    if (fmt) setImportFormat(fmt);
    setImportText(await file.text());
  };

  const downloadTemplate = () => {
    if (!template.data) return;
    const url = URL.createObjectURL(new Blob([template.data.csv], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "reading-labels-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const list = scores.data?.scores ?? [];
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="reading-accuracy" onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer">
        <span className="font-semibold">{t("boq.takeoff.accuracy.title", "Reading accuracy")}</span>
        {list[0] ? <span className={`ml-2 ${MUTED}`}>{headline(list[0].totals)}</span> : null}
        {list[0] && list[0].status === "REGRESSION" ? <span className="ml-2"><Badge tone="red">{statusLabel("REGRESSION")}</Badge></span> : null}
      </summary>
      <div className="mt-2 space-y-3">
        <section data-testid="accuracy-labels">
          <p className="font-semibold">{t("boq.takeoff.accuracy.labels", "Labelled examples")}</p>
          <p className={MUTED} data-testid="accuracy-labels-line">{labels.isLoading ? "…" : labelsLine(labels.data)}</p>
          {labels.data && labels.data.unlabelled_sheets.length ? (
            <p className={MUTED}>{`Sheets without a label: ${labels.data.unlabelled_sheets.join(", ")}`}</p>
          ) : null}
          {canEdit ? (
            <div className="mt-1 flex flex-wrap gap-2">
              <button type="button" className={BTN} disabled={derive.isPending} onClick={onDerive} data-testid="accuracy-derive">{t("boq.takeoff.accuracy.derive", "Make labels from the register")}</button>
              <button type="button" className={BTN} onClick={() => setImportOpen((v) => !v)} aria-expanded={importOpen} data-testid="accuracy-import-toggle">{t("boq.takeoff.accuracy.importBtn", "Import ground truth")}</button>
            </div>
          ) : null}
          {importOpen && canEdit ? (
            <div className="mt-2 space-y-1.5" data-testid="accuracy-import">
              <p className={MUTED}>{t("boq.takeoff.accuracy.importHint", "A CSV or JSON file of what is really on the drawing, one member to a row. Download the template for the columns.")}</p>
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" className={BTN} onClick={downloadTemplate} disabled={!template.data}>{t("boq.takeoff.accuracy.template", "Download template")}</button>
                <input type="file" accept=".csv,.json,text/csv,application/json" onChange={(e) => void onFile(e.target.files?.[0])} aria-label={t("boq.takeoff.accuracy.file", "Ground-truth file")} />
                <select value={importFormat} onChange={(e) => setImportFormat(e.target.value as "CSV" | "JSON")} aria-label="Format" className="rounded-[8px] border border-[var(--color-border)] bg-transparent px-1 py-0.5">
                  <option value="CSV">CSV</option>
                  <option value="JSON">JSON</option>
                </select>
              </div>
              <textarea value={importText} onChange={(e) => setImportText(e.target.value)} rows={5} className="w-full rounded-[8px] border border-[var(--color-border)] bg-transparent p-2 font-mono text-[11.5px]" aria-label={t("boq.takeoff.accuracy.content", "Ground-truth content")} data-testid="accuracy-import-text" />
              <label className="flex items-center gap-1.5"><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />{t("boq.takeoff.accuracy.replace", "Replace the labels imported earlier")}</label>
              <button type="button" className={BTN} disabled={!importText.trim() || importer.isPending} onClick={onImport} data-testid="accuracy-import-go">{t("boq.takeoff.accuracy.importGo", "Import")}</button>
            </div>
          ) : null}
        </section>

        {canEdit ? (
          <section data-testid="accuracy-run">
            <p className="font-semibold">{t("boq.takeoff.accuracy.score", "Score the reader")}</p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-1.5">
                {t("boq.takeoff.accuracy.mode", "Score")}
                <select value={mode} onChange={(e) => setMode(e.target.value as ScoreMode)} className="rounded-[8px] border border-[var(--color-border)] bg-transparent px-1 py-0.5" data-testid="accuracy-mode">
                  <option value="DRY_RUN">{t("boq.takeoff.accuracy.modeDry", "Read the sheets again (nothing is saved to the drawing)")}</option>
                  <option value="STORED">{t("boq.takeoff.accuracy.modeStored", "The items already found")}</option>
                </select>
              </label>
              <label className="flex items-center gap-1.5"><input type="checkbox" checked={marksOnly} onChange={(e) => setMarksOnly(e.target.checked)} />{t("boq.takeoff.accuracy.marksOnly", "Match by mark only")}</label>
            </div>
            <details className="mt-1">
              <summary className="cursor-pointer text-[11.5px]">{t("boq.takeoff.accuracy.advanced", "More")}</summary>
              <div className="mt-1 space-y-1">
                <label className="block">{t("boq.takeoff.accuracy.labelDrawing", "Labels of another drawing (its id)")}
                  <input value={labelDrawingId} onChange={(e) => setLabelDrawingId(e.target.value)} className="mt-0.5 w-full rounded-[8px] border border-[var(--color-border)] bg-transparent px-2 py-1 font-mono text-[11.5px]" />
                </label>
                <label className="block">{t("boq.takeoff.accuracy.note", "Note")}
                  <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} className="mt-0.5 w-full rounded-[8px] border border-[var(--color-border)] bg-transparent px-2 py-1 text-[11.5px]" />
                </label>
              </div>
            </details>
            <div className="mt-1.5 flex items-center gap-2">
              <button type="button" className={BTN} disabled={Boolean(blocked) || run.isPending} onClick={onRun} data-testid="accuracy-run-go">{run.isPending ? t("boq.takeoff.accuracy.running", "Scoring…") : t("boq.takeoff.accuracy.runGo", "Run score")}</button>
              {blocked ? <span className={MUTED} data-testid="accuracy-blocked">{blocked}</span> : null}
            </div>
          </section>
        ) : null}

        <section data-testid="accuracy-scores">
          <p className="font-semibold">{t("boq.takeoff.accuracy.history", "Scores so far")}</p>
          {scores.isError ? <p className="text-[var(--color-danger,#b42318)]">{t("boq.takeoff.accuracy.loadError", "Could not load the scores.")}</p> : null}
          {!scores.isLoading && !list.length ? <p className={MUTED}>{t("boq.takeoff.accuracy.none", "No score yet.")}</p> : null}
          {list.length ? (
            <ul className="mt-1 space-y-1">
              {list.map((s) => (
                <ScoreRow key={s.id} s={s} selected={picked.includes(s.id)} open={shown === s.id} onPick={() => setPicked((p) => toggleCompare(p, s.id))} onOpen={() => setShown((x) => (x === s.id ? null : s.id))} />
              ))}
            </ul>
          ) : null}
          {list.length > 1 ? <p className={`mt-1 ${MUTED}`}>{t("boq.takeoff.accuracy.pickTwo", "Tick two scores to see what changed between them.")}</p> : null}
          {picked.length === 2 && cmp.data ? <CompareView cmp={cmp.data.comparison} /> : null}
          {picked.length === 2 && cmp.isError ? <p className="text-[var(--color-danger,#b42318)]">{t("boq.takeoff.accuracy.compareError", "Could not compare these scores.")}</p> : null}
          {shown && shownScore.data ? <ScoreView detail={shownScore.data} /> : null}
          {shown && shownScore.isLoading ? <p className={MUTED}>{"…"}</p> : null}
        </section>
      </div>
    </details>
  );
}
