import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState, Modal, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { MATCH_PAGE_SIZE } from "../api/bbsMatch.api";
import { useBbsMatchItems, useBbsMatchRun, useConfirmBbsMatch, useForgetBbsMatch, useRunBbsMatch, useSaveFloorMap } from "../hooks/useBbsMatch";
import { CLASSES, FLOORS, GATE_SHARE, KIND_ORDER, confirmPayload, confirmProblem, elementLabel, floorMapChanged, gateMet, itemWhere, kindTone, methodLabel, orderedFloorMap, sharePercent, sortedFamilies } from "../utils/bbsMatch";
import type { BbsDocumentSummary } from "../types/bbsAudit.types";
import type { AskGroup, MatchKind } from "../types/bbsMatch.types";

interface BbsMatchDialogProps {
  projectId: string;
  document: BbsDocumentSummary;
  canEdit: boolean;
  onClose: () => void;
}

const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const field = "rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[12px]";

export function BbsMatchDialog({ projectId, document, canEdit, onClose }: BbsMatchDialogProps) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [kind, setKind] = useState<MatchKind | "">("ASK");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [edited, setEdited] = useState<Record<string, string[]>>({});
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [cls, setCls] = useState("COLUMN");
  const [mark, setMark] = useState("");
  const [floor, setFloor] = useState("");
  const [reviewedOnly, setReviewedOnly] = useState(false);
  const [note, setNote] = useState("");
  const run = useBbsMatchRun(document.id);
  const items = useBbsMatchItems(document.id, { kind, family: "", page });
  const start = useRunBbsMatch(document.id, projectId);
  const confirm = useConfirmBbsMatch(document.id, projectId);
  const forget = useForgetBbsMatch(document.id, projectId);
  const saveMap = useSaveFloorMap(document.id, projectId);
  const stats = run.data?.stats;
  const data = items.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / MATCH_PAGE_SIZE)) : 1;
  const runFloorMap = run.data?.floor_map;
  useEffect(() => { setEdited(runFloorMap ?? {}); }, [runFloorMap]);
  const mapChanged = useMemo(() => floorMapChanged(runFloorMap ?? {}, edited), [runFloorMap, edited]);
  const problemText: Record<string, string> = {
    "mark-needed": t("bbs.match.markNeeded", "Give the mark as it is on the drawing."),
    "class-needed": t("bbs.match.classNeeded", "Choose the kind of member."),
    "floor-unknown": t("bbs.match.floorUnknown", "Choose one of the listed floors."),
    "note-needed": t("bbs.match.noteNeeded", "Say why this row has no drawing member."),
    "note-too-long": t("bbs.match.noteLong", "The note is longer than 500 characters."),
  };

  function startMatch() {
    setError(null);
    start.mutate(undefined, {
      onSuccess: () => { setPage(1); showToast({ tone: "success", title: t("bbs.match.done", "Matching finished") }); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.match.error", "Couldn't match the schedule to the drawings."))),
    });
  }

  function saveFloors() {
    setError(null);
    saveMap.mutate(edited, {
      onSuccess: () => showToast({ tone: "success", title: t("bbs.match.floorsSaved", "Floor map confirmed") }),
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.match.floorsError", "Couldn't save the floor map."))),
    });
  }

  function submit(g: AskGroup) {
    const problem = confirmProblem(cls, mark, floor, reviewedOnly, note);
    if (problem) { setError(problemText[problem] ?? problem); return; }
    setError(null);
    confirm.mutate(confirmPayload(g, cls, mark, floor, reviewedOnly, note), {
      onSuccess: () => { setOpenGroup(null); setMark(""); setNote(""); setReviewedOnly(false); },
      onError: (e) => setError(getApiErrorMessage(e, t("bbs.match.confirmError", "Couldn't save this match."))),
    });
  }

  return (
    <Modal title={t("bbs.match.title", "Match to drawings · version {{v}}", { v: document.version })} description={document.file_name ?? undefined} onClose={onClose} wide>
      <div className="space-y-4" data-testid="bbs-match-dialog">
        <div className="flex flex-wrap items-center gap-2">
          {stats ? (
            <>
              <Badge tone={gateMet(run.data) ? "green" : "gold"}>{t("bbs.match.share", "{{p}} matched without asking", { p: sharePercent(stats.share_without_asking) })}</Badge>
              <span className="text-[12px] text-[var(--color-text-muted)]">{t("bbs.match.gate", "target {{p}}", { p: sharePercent(GATE_SHARE) })}</span>
              <Badge tone="blue">{t("bbs.match.rows", "{{n}} rows", { n: stats.rows })}</Badge>
              <Badge tone="gold">{t("bbs.match.ask", "{{n}} to confirm", { n: stats.ask })}</Badge>
              <Badge tone="red">{t("bbs.match.extra", "{{n}} not on drawings", { n: stats.extra })}</Badge>
              <Badge tone="red">{t("bbs.match.missing", "{{n}} drawn, no row", { n: data?.counts_by_kind.MISSING ?? 0 })}</Badge>
            </>
          ) : null}
          {canEdit ? (
            <div className="ml-auto">
              <Button variant="secondary" size="sm" disabled={start.isPending} onClick={startMatch}>
                {start.isPending ? t("bbs.match.running", "Matching…") : run.data ? t("bbs.match.rerun", "Match again") : t("bbs.match.run", "Match to drawings")}
              </Button>
            </div>
          ) : null}
        </div>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        {stats ? (
          <div className="space-y-1 text-[12px] text-[var(--color-text-secondary)]">
            <div>{t("bbs.match.sheetOnly", "{{n}} slab rows are matched to the floor plan only; the room is not checked because no room names were read.", { n: stats.room_check_skipped })}</div>
            <div className="flex flex-wrap gap-2">
              {sortedFamilies(stats).map(([f, m, n]) => <Badge key={f} tone={m === n ? "green" : "gold"}>{f} {m}/{n}</Badge>)}
            </div>
          </div>
        ) : null}

        {run.data ? (
          <details className="rounded-[8px] border border-[var(--color-border)] p-3">
            <summary className="cursor-pointer text-[12.5px] font-semibold">
              {run.data.floor_map_confirmed ? t("bbs.match.floorMapConfirmed", "Floor map (confirmed)") : t("bbs.match.floorMapProposed", "Floor map (proposed from the drawings, not yet confirmed)")}
            </summary>
            <div className="mt-2 space-y-1.5">
              {orderedFloorMap(edited).map(([name, floors]) => (
                <label key={name} className="flex items-center gap-2 text-[12px]">
                  <span className="min-w-[220px] text-[var(--color-text-primary)]">{name}</span>
                  <select className={field} value={floors[0] ?? ""} disabled={!canEdit} onChange={(e) => setEdited({ ...edited, [name]: [e.target.value] })}>
                    {FLOORS.map((f) => <option key={f} value={f}>{f}</option>)}
                  </select>
                </label>
              ))}
              {canEdit ? <Button variant="primary" size="sm" disabled={saveMap.isPending || !mapChanged && run.data.floor_map_confirmed} onClick={saveFloors}>{t("bbs.match.confirmFloors", "Confirm floor map")}</Button> : null}
            </div>
          </details>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          {KIND_ORDER.map((k) => (
            <Button key={k} variant={kind === k ? "primary" : "ghost"} size="sm" onClick={() => { setKind(k); setPage(1); }}>{k} {data?.counts_by_kind[k] ?? ""}</Button>
          ))}
        </div>

        {items.isLoading ? <LoadingState label={t("bbs.match.loading", "Loading…")} /> : items.isError ? (
          <ErrorState title={t("bbs.match.loadError", "Couldn't load the matches")} onRetry={() => void items.refetch()} />
        ) : !data || data.run_id === null ? (
          <EmptyState title={t("bbs.match.none", "Not matched yet")} description={t("bbs.match.noneDesc", "Run the match once the structural drawings have been prepared.")} />
        ) : kind === "ASK" ? (
          data.asks.length === 0 ? <EmptyState title={t("bbs.match.noAsks", "Nothing to confirm")} description={t("bbs.match.noAsksDesc", "Every row has been matched or decided.")} /> : (
            <ul className="space-y-2">
              {data.asks.map((g) => (
                <li key={g.group} className="rounded-[8px] border border-[var(--color-border)] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[12.5px] font-semibold">{g.group.replace("|", " · ")}</span>
                    <Badge tone="gold">{t("bbs.match.askRows", "{{n}} rows", { n: g.rows })}</Badge>
                    <span className="text-[12px] text-[var(--color-text-muted)]">{g.reason}</span>
                    {canEdit ? <Button variant="ghost" size="sm" onClick={() => setOpenGroup(openGroup === g.group ? null : g.group)}>{t("bbs.match.confirm", "Confirm")}</Button> : null}
                  </div>
                  {openGroup === g.group ? (
                    <div className="mt-2 flex flex-wrap items-end gap-2">
                      <label className="text-[11px]">{t("bbs.match.kindLabel", "Member")}
                        <select className={`${field} block`} value={cls} disabled={reviewedOnly} onChange={(e) => setCls(e.target.value)}>{CLASSES.map((c) => <option key={c}>{c}</option>)}</select>
                      </label>
                      <label className="text-[11px]">{t("bbs.match.markLabel", "Mark on drawing")}
                        <input className={`${field} block`} value={mark} disabled={reviewedOnly} onChange={(e) => setMark(e.target.value)} />
                      </label>
                      <label className="text-[11px]">{t("bbs.match.floorLabel", "Floor")}
                        <select className={`${field} block`} value={floor} disabled={reviewedOnly} onChange={(e) => setFloor(e.target.value)}>
                          <option value="">—</option>{FLOORS.map((f) => <option key={f}>{f}</option>)}
                        </select>
                      </label>
                      <label className="flex items-center gap-1 text-[11px]"><input type="checkbox" checked={reviewedOnly} onChange={(e) => setReviewedOnly(e.target.checked)} />{t("bbs.match.reviewedOnly", "Reviewed: no drawing member")}</label>
                      <label className="text-[11px]">{t("bbs.match.noteLabel", "Note")}
                        <input className={`${field} block`} value={note} onChange={(e) => setNote(e.target.value)} />
                      </label>
                      <Button variant="primary" size="sm" disabled={confirm.isPending} onClick={() => submit(g)}>{t("bbs.match.save", "Save match")}</Button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )
        ) : data.items.length === 0 ? <EmptyState title={t("bbs.match.noItems", "No rows here")} description={t("bbs.match.noItemsDesc", "No row falls in this group.")} /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead><tr>
                <th className={th}>{t("bbs.match.col.row", "Schedule row")}</th>
                <th className={th}>{t("bbs.match.col.drawing", "Drawing member")}</th>
                <th className={th}>{t("bbs.match.col.how", "How")}</th>
                <th className={`${th} text-right`}>{t("bbs.match.col.conf", "Confidence")}</th>
                <th className={th}>{t("bbs.match.col.note", "Note")}</th>
                <th className={`${th} text-right`}>{canEdit ? t("bbs.col.actions", "Actions") : ""}</th>
              </tr></thead>
              <tbody>
                {data.items.map((i) => (
                  <tr key={i.id} className="border-t border-[var(--color-border)]">
                    <td className="px-3 py-2 text-[12.5px]">{itemWhere(i)}</td>
                    <td className="px-3 py-2 text-[12px]">{i.elements.length ? i.elements.map(elementLabel).join(", ") : "—"}</td>
                    <td className="px-3 py-2"><Badge tone={kindTone(i.kind)}>{i.kind === "MATCH" ? methodLabel(i.method) : i.kind}</Badge></td>
                    <td className="px-3 py-2 text-right font-mono text-[12px]">{i.confidence.toFixed(2)}</td>
                    <td className="px-3 py-2 text-[12px] text-[var(--color-text-secondary)]">{i.reason ?? i.basis ?? ""}</td>
                    <td className="px-3 py-2 text-right">
                      {canEdit && i.method === "USER" && i.sheet_name && i.member ? (
                        <Button variant="ghost" size="sm" disabled={forget.isPending} onClick={() => forget.mutate(`${i.sheet_name}|${i.member}`, { onError: (e) => setError(getApiErrorMessage(e, t("bbs.match.forgetError", "Couldn't withdraw this match."))) })}>
                          {t("bbs.match.withdraw", "Withdraw")}
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > MATCH_PAGE_SIZE && kind !== "ASK" ? (
          <div className="flex items-center justify-end gap-2 text-[12px]">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</Button>
            <span>{page} / {pages}</span>
            <Button variant="ghost" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>›</Button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
