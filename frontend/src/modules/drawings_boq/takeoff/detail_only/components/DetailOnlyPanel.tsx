import { useTranslation } from "react-i18next";
import { Badge, useToast } from "../../../../organizations/components/OrganizationUi";
import { useChooseBeamDepth, useChooseColumnMark, useDetailOnly, useUndoDetailChoice } from "../hooks/useDetailOnly";
import { takeoffErrorMessage } from "../../utils/errors";
import { beamLine, decisionText, gapText, isEmpty, offeredMarks, optionText, pagesText, perMetreText, perPieceText, proposalText, sizeText, stakeText, summaryLine } from "../utils/detailOnly";

interface Props {
  drawingId: string;
  canEdit: boolean;
}

const BTN = "rounded-[8px] border border-[var(--color-border)] px-2 py-0.5 text-[11.5px] disabled:opacity-50";
const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";

export function DetailOnlyPanel({ drawingId, canEdit }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const report = useDetailOnly(drawingId);
  const chooseMark = useChooseColumnMark(drawingId);
  const chooseDepth = useChooseBeamDepth(drawingId);
  const undo = useUndoDetailChoice(drawingId);
  const busy = chooseMark.isPending || chooseDepth.isPending || undo.isPending;
  const fail = (title: string) => (e: unknown) => showToast({ tone: "error", title, description: takeoffErrorMessage(e) });
  const data = report.data;
  if (report.isLoading || (report.isError && !data)) return null;
  if (isEmpty(data) || !data) return null;
  const line = summaryLine(data);
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="detail-only">
      <summary className="cursor-pointer">
        <span className="font-semibold">{t("boq.takeoff.detailOnly.title", "Marks with a detail and no place on the plans")}</span>
        {line ? <span className={`ml-2 ${MUTED}`}>{line}</span> : null}
      </summary>
      <div className="mt-2 space-y-3">
        <p className={MUTED}>{t("boq.takeoff.detailOnly.hint", "These marks are drawn as a detail but the reader found no place for them on the plans. Nothing is added to your measurements from this list: a mark is given to shapes, or a depth to a beam, only when you choose it.")}</p>

        {data.columns.length ? (
          <section data-testid="detail-only-columns">
            <p className="font-semibold">{t("boq.takeoff.detailOnly.columns", "Columns")}</p>
            <ul className="mt-1 space-y-2">
              {data.columns.map((c) => (
                <li key={c.mark} data-testid={`detail-only-column-${c.mark}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-semibold">{c.mark}</span>
                    <span>{sizeText(c.size_mm)}</span>
                    <span className={MUTED}>{pagesText(c.detail_pages)}</span>
                    {c.detail_disagree ? <Badge tone="gold">{t("boq.takeoff.detailOnly.disagree", "Details disagree")}</Badge> : null}
                  </div>
                  <p className={MUTED}>{perPieceText(c.per_piece)}</p>
                  {c.proposals.length ? (
                    <ul className="mt-1 space-y-1 border-l border-[var(--color-border)] pl-2">
                      {c.proposals.map((p) => (
                        <li key={p.candidate_id} className="flex flex-wrap items-center gap-2" data-testid={`detail-only-proposal-${p.candidate_id}`}>
                          <span>{proposalText(p)}</span>
                          {p.other_marks.length ? <span className={MUTED}>{`also fits ${p.other_marks.join(", ")}`}</span> : null}
                          {canEdit ? offeredMarks(c, p).map((m) => (
                            <button key={m} type="button" className={BTN} disabled={busy}
                              onClick={() => chooseMark.mutate({ candidate_id: p.candidate_id, mark: m }, { onError: fail(t("boq.takeoff.detailOnly.markError", "Could not give the mark")) })}
                              data-testid={`detail-only-choose-${p.candidate_id}-${m}`}>
                              {t("boq.takeoff.detailOnly.thisIs", "These are {{mark}}", { mark: m })}
                            </button>
                          )) : null}
                        </li>
                      ))}
                    </ul>
                  ) : <p className={MUTED}>{t("boq.takeoff.detailOnly.noShapes", "No unmarked shape of this size offers it: the mark is on no plan.")}</p>}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {data.beams.length ? (
          <section data-testid="detail-only-beams">
            <p className="font-semibold">{t("boq.takeoff.detailOnly.beams", "Beams")}</p>
            <ul className="mt-1 space-y-1.5">
              {data.beams.map((b) => (
                <li key={b.mark} data-testid={`detail-only-beam-${b.mark}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-semibold">{b.mark}</span>
                    <span>{beamLine(b)}</span>
                    <span className={MUTED}>{pagesText(b.detail_pages)}</span>
                    {b.detail_disagree ? <Badge tone="gold">{t("boq.takeoff.detailOnly.disagree", "Details disagree")}</Badge> : null}
                  </div>
                  <p className={MUTED}>{perMetreText(b.per_metre, b.depth_read)}</p>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {data.depth_gaps.length ? (
          <section data-testid="detail-only-gaps">
            <p className="font-semibold">{t("boq.takeoff.detailOnly.gaps", "Beams on the plans without a depth")}</p>
            <ul className="mt-1 space-y-2">
              {data.depth_gaps.map((g) => (
                <li key={g.mark} data-testid={`detail-only-gap-${g.mark}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span>{gapText(g)}</span>
                    <span className={MUTED}>{g.rows.map((r) => `${r.length_m.toFixed(1)} m${r.page_no ? ` (sheet ${r.page_no})` : ""}`).join(", ")}</span>
                  </div>
                  {stakeText(g) ? <p className={MUTED}>{stakeText(g)}</p> : null}
                  {g.options.length ? (
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className={MUTED}>{t("boq.takeoff.detailOnly.useDepth", "Use the depth printed for another beam of this kind:")}</span>
                      {canEdit ? g.options.map((o) => (
                        <button key={o.depth_mm} type="button" className={BTN} disabled={busy}
                          onClick={() => chooseDepth.mutate({ mark: g.mark, depth_mm: o.depth_mm }, { onError: fail(t("boq.takeoff.detailOnly.depthError", "Could not set the depth")) })}
                          data-testid={`detail-only-depth-${g.mark}-${Math.round(o.depth_mm)}`}>
                          {optionText(o)}
                        </button>
                      )) : g.options.map((o) => <span key={o.depth_mm}>{optionText(o)}</span>)}
                    </div>
                  ) : <p className={MUTED}>{t("boq.takeoff.detailOnly.noOptions", "No other beam of this kind prints a depth. Type it when you accept the beam.")}</p>}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {data.decisions.length ? (
          <section data-testid="detail-only-decisions">
            <p className="font-semibold">{t("boq.takeoff.detailOnly.decisions", "Your choices")}</p>
            <ul className="mt-1 space-y-1">
              {data.decisions.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-2" data-testid={`detail-only-decision-${d.id}`}>
                  <span>{decisionText(d)}</span>
                  {d.kind === "BEAM_DEPTH" && d.applied ? <Badge tone="gold">{t("boq.takeoff.detailOnly.assumed", "Assumed")}</Badge> : null}
                  {!d.applied ? <Badge tone="slate">{t("boq.takeoff.detailOnly.notApplied", "Not applied")}</Badge> : null}
                  {canEdit ? (
                    <button type="button" className={BTN} disabled={busy} onClick={() => undo.mutate(d.id, { onError: fail(t("boq.takeoff.detailOnly.undoError", "Could not take the choice back")) })}>
                      {t("boq.takeoff.detailOnly.undo", "Take back")}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {data.summary.cut ? <p className={MUTED}>{t("boq.takeoff.detailOnly.cut", "{{count}} more are not listed.", { count: data.summary.cut })}</p> : null}
      </div>
    </details>
  );
}
