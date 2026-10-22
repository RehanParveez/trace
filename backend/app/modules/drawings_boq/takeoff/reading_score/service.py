from __future__ import annotations
import asyncio
import logging
from app.modules.drawings_boq.takeoff.reading_score.models import ReadingLabel, ReadingScore
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.reading_score.repository import ReadingScoreRepository
from uuid import UUID
from decimal import Decimal
from app.core.exceptions import TraceException
import time
import uuid
from datetime import datetime, timezone
from app.modules.drawings_boq.takeoff.reading_score import labels as L
from app.modules.drawings_boq.takeoff import reading_score as S
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract.pipeline import run_extraction
from app.modules.drawings_boq.takeoff.extract.structure import column_details
from app.modules.drawings_boq.takeoff.prep.analyze import ANALYSIS_VERSION

log = logging.getLogger(__name__)

MODES = ("DRY_RUN", "STORED")
NOT_JUDGED = {
  "NO_LABELS": "No label on this sheet, so there is nothing to score it against.",
  "NOT_READ": "The sheet has not been read yet.",
  "NOT_PREPARED": "The sheet has not been prepared (its drawing has not been read).",
  "NO_SCALE": "The sheet has no usable scale, so the reader cannot run on it.",
  "READ_FAILED": "The reader failed on this sheet.",
  "TIME_LIMIT": "The run ran out of time before this sheet.",
  "NO_MATCHING_SHEET": "The labels name a sheet number this drawing does not have.",
  "NOT_SELECTED": "The sheet was not among the sheets asked for.",
}

class Unreadable(Exception):
  def __init__(self, code: str, detail: str | None = None):
    self.code, self.detail = code, detail
    super().__init__(code)

def _f(v) -> float | None:
  return None if v is None else float(v)

def _label_dict(r: ReadingLabel) -> dict:
  return {"id": str(r.id), "sheet_id": r.sheet_id, "family": r.family, "mark": r.mark, "polarity": r.polarity, "x_pt": _f(r.x_pt), "y_pt": _f(r.y_pt),
    "attrs": dict(r.attrs or {}), "complete": bool(r.complete), "source": r.source, "source_ref": r.source_ref, "extract_version": r.extract_version}

def _totals(result: dict) -> dict:
  t = result["totals"]
  return {k: t.get(k) for k in ("labels", "found", "tp", "fp", "fn", "precision", "recall", "f1")}

def score_item(row: ReadingScore) -> dict:
  return {"id": row.id, "drawing_id": row.drawing_id, "label_drawing_id": row.label_drawing_id, "created_at": row.created_at, "mode": row.mode, "status": row.status,
    "extract_version": row.extract_version, "analysis_version": row.analysis_version, "label_count": row.label_count, "partial": bool((row.result or {}).get("partial")),
    "rule_hash": row.rule_hash, "labels_stamp": row.labels_stamp, "totals": _totals(row.result), "note": row.note}

class ReadingScoreService(ExtractService):
  def __init__(self, session):
    super().__init__(session)
    self.store = ReadingScoreRepository(session)

  async def _drawing(self, org: UUID, drawing_id: UUID):
    return await self.core._pdf_drawing(org, drawing_id)

  async def labels_summary(self, org: UUID, drawing_id: UUID) -> dict:
    await self._drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self.store.labels(org, drawing_id)
    
    per: dict = {}
    fam: dict = {}
    for r in rows:
      s = per.setdefault(r.sheet_id, {"positive": 0, "negative": 0, "complete": True, "sources": set()})
      s["positive" if r.polarity == L.POSITIVE else "negative"] += 1
      s["complete"] = s["complete"] and bool(r.complete)
      s["sources"].add(r.source)
      f = fam.setdefault(r.family, {"family": r.family, "positive": 0, "negative": 0})
      f["positive" if r.polarity == L.POSITIVE else "negative"] += 1
    out_sheets = [{"sheet_id": s.id, "page_no": s.page_no, "title": getattr(s, "label", None), "positive": per[s.id]["positive"], "negative": per[s.id]["negative"],
      "complete": per[s.id]["complete"], "sources": sorted(per[s.id]["sources"])} for s in sheets if s.id in per]
    return {"drawing_id": drawing_id, "labels": len(rows), "positive": sum(1 for r in rows if r.polarity == L.POSITIVE), "negative": sum(1 for r in rows if r.polarity == L.NEGATIVE),
      "stamp": L.stamp([_label_dict(r) for r in rows]) if rows else None, "sheets": out_sheets, "families": sorted(fam.values(), key=lambda x: x["family"]),
      "unlabelled_sheets": [s.page_no for s in sheets if s.id not in per]}

  def label_template(self) -> dict:
    return {"columns": list(L.IMPORT_COLUMNS), "csv": L.import_template(), "families": [*[c for c in L.CATEGORIES if c != "SITE"], *[f"SITE:{k}" for k in L.SITE_KINDS]]}

  async def derive_labels(self, org: UUID, user_id: UUID, drawing_id: UUID) -> dict:
    drawing = await self._drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    cands = await self.repo.candidates(org, [s.id for s in sheets])
    new, report = L.labels_from_register(cands)
    have = {(r.source_ref): r for r in await self.store.labels(org, drawing_id, L.REGISTER)}
    added = updated = unchanged = 0
    wanted: set = set()
    
    for l in new:
      wanted.add(l["source_ref"])
      row = have.get(l["source_ref"])
      x = None if l["x_pt"] is None else Decimal(str(round(l["x_pt"], 4)))
      y = None if l["y_pt"] is None else Decimal(str(round(l["y_pt"], 4)))
      
      if row is None:
        self.store.add_labels([ReadingLabel(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, sheet_id=l["sheet_id"], family=l["family"], mark=l["mark"],
          polarity=l["polarity"], x_pt=x, y_pt=y, attrs=l["attrs"], complete=l["complete"], source=L.REGISTER, source_ref=l["source_ref"],
          extract_version=l["extract_version"], created_by_user_id=user_id)])
        added += 1
      else:
        same = (row.family, row.mark, row.polarity, _f(row.x_pt), _f(row.y_pt), dict(row.attrs or {}), bool(row.complete)) == (l["family"], l["mark"], l["polarity"],
          None if x is None else float(x), None if y is None else float(y), l["attrs"], l["complete"])
        if same:
          unchanged += 1
        else:
          row.family, row.mark, row.polarity, row.x_pt, row.y_pt, row.attrs, row.complete = l["family"], l["mark"], l["polarity"], x, y, l["attrs"], l["complete"]
          row.extract_version = l["extract_version"]
          updated += 1
          
    alive = {str(c.id) for c in cands}
    revoke = [r.id for ref, r in have.items() if ref not in wanted and ref.rsplit(":", 1)[0] in alive]
    revoked = await self.store.delete_labels(org, drawing_id, L.REGISTER, ids=revoke)
    await self.session.flush()
    await self.session.commit()
    return {"drawing_id": drawing_id, "added": added, "updated": updated, "unchanged": unchanged, "revoked": revoked, "report": report,
      "summary": await self.labels_summary(org, drawing_id)}

  async def import_labels(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    drawing = await self._drawing(org, drawing_id)
    try:
      rows = L.parse_import(payload.content, payload.format)
    except L.LabelError as e:
      raise TraceException(str(e), status_code=422, code="LABEL_FILE_INVALID")
    sheets = {s.page_no: s for s in await self.core.repo.sheets(org, drawing_id)}
    missing = sorted({r["page_no"] for r in rows} - set(sheets))
    if missing:
      raise TraceException(f"This drawing has no sheet number {', '.join(str(p) for p in missing[:10])}. Nothing was imported.", status_code=422, code="LABEL_SHEET_NOT_FOUND")
    deleted = await self.store.delete_labels(org, drawing_id, L.IMPORT) if payload.replace_imported else 0
    batch = uuid.uuid4().hex[:12]
    self.store.add_labels([ReadingLabel(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, sheet_id=sheets[r["page_no"]].id, family=r["family"], mark=r["mark"],
      polarity=r["polarity"], x_pt=None if r["x_pt"] is None else Decimal(str(round(r["x_pt"], 4))), y_pt=None if r["y_pt"] is None else Decimal(str(round(r["y_pt"], 4))),
      attrs=r["attrs"], complete=r["complete"], source=L.IMPORT, source_ref=f"{batch}:{i}", extract_version=None, created_by_user_id=user_id) for i, r in enumerate(rows)])
    
    await self.session.flush()
    await self.session.commit()
    return {"drawing_id": drawing_id, "added": len(rows), "deleted": deleted, "sheets": len({r["page_no"] for r in rows}), "summary": await self.labels_summary(org, drawing_id)}

  async def delete_labels(self, org: UUID, drawing_id: UUID, source: str | None) -> dict:
    await self._drawing(org, drawing_id)
    if source not in (None, L.REGISTER, L.IMPORT):
      raise TraceException("source is REGISTER or IMPORT.", status_code=422, code="LABEL_SOURCE_INVALID")
    n = await self.store.delete_labels(org, drawing_id, source)
    await self.session.commit()
    return {"drawing_id": drawing_id, "deleted": n, "summary": await self.labels_summary(org, drawing_id)}

  async def _dry_read(self, org: UUID, sheet, budget_s: float) -> list:
    if sheet.prep_status != "READY":
      raise Unreadable("NOT_PREPARED")
    cal, ev = await self._scale(org, sheet)
    
    if ev is None:
      raise Unreadable("NO_SCALE")
    try:
      index = await self.prep._index(org, sheet.id)
      mm_per_pt = float(ev.mm_per_pt)
      unverified = "PDF_RATIO_UNVERIFIED" in (ev.warnings or ())
      schedule = await self.prep.drawing_schedule(org, sheet.drawing_id)
      floor_heights = await self.prep.drawing_storey_heights(org, sheet.drawing_id)
      slab_values = await self.prep.drawing_slab_values(org, sheet.drawing_id)
      beam_sections = await self.prep.drawing_beam_sections(org, sheet.drawing_id)
      tank_details = await self.prep.drawing_tank_details(org, sheet.drawing_id)
      footing_sections = await self.prep.drawing_footing_sections(org, sheet.drawing_id)
      units = await self.prep.drawing_units(org, sheet.drawing_id)
      wall_vocab = await self.prep.drawing_wall_vocab(org, sheet.drawing_id, units["imperial"])
      title = (sheet.prep_meta or {}).get("title") or {}
      level_hint = None if title.get("composite") else title.get("level_hint")
      floors = self.prep._floor_keys(await self.prep.repo.sheets(org, sheet.drawing_id))
      lowest_level = bool(level_hint) and bool(floors) and floors[0] == level_hint
      result = await asyncio.to_thread(run_extraction, index, mm_per_pt, composite=bool(title.get("composite")), regions_only=False, cal_factor=float(ev.factor),
        scale_unverified=unverified, content_kind=sheet.content_kind, budget_s=float(budget_s), schedule=schedule, views_meta=(sheet.prep_meta or {}).get("views"), frame=(sheet.prep_meta or {}).get("frame"),
        col_details=column_details(sheet.prep_meta), floor_heights=floor_heights, level_hint=level_hint, slab_values=slab_values, text_source=(sheet.prep_meta or {}).get("text_source", "TEXT"), scan_reading=(sheet.prep_meta or {}).get("scan_reading"),
        lowest_level=lowest_level, with_finishes=True, beam_sections=beam_sections, tank_details=tank_details,
        imperial=units["imperial"], wall_vocab=wall_vocab, footing_sections=footing_sections)
    except TraceException:
      raise
    except Exception as e:
      log.exception("Scoring read failed for sheet %s", sheet.id)
      raise Unreadable("READ_FAILED", type(e).__name__)
    return list(result.candidates)

  async def _reads(self, org: UUID, sheet, mode: str, budget_s: float) -> tuple:
    if mode == "STORED":
      ext = await self.repo.extraction(org, sheet.id)
      if ext is None:
        raise Unreadable("NOT_READ")
      rows = await self.repo.candidates(org, [sheet.id])
      units = [u for r in rows for u in L.units_of_candidate(r, ref=str(r.id))]
      return units, max([r.extract_version for r in rows] or [ext.extract_version])
    cands = await self._dry_read(org, sheet, budget_s)
    return [u for c in cands for u in L.units_of_candidate(c, ref=c.key)], C.EXTRACT_VERSION

  async def run_score(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    drawing = await self._drawing(org, drawing_id)
    mode = str(payload.mode or "DRY_RUN").upper()
    
    if mode not in MODES:
      raise TraceException("mode is DRY_RUN or STORED.", status_code=422, code="SCORE_MODE_INVALID")
    try:
      rule = S.MatchRule.from_dict(payload.rule)
    except ValueError as e:
      raise TraceException(str(e), status_code=422, code="SCORE_RULE_INVALID")
    label_drawing = payload.label_drawing_id or drawing_id
    if label_drawing != drawing_id:
      await self._drawing(org, label_drawing)
    label_rows = await self.store.labels(org, label_drawing)
    if not label_rows:
      raise TraceException("There are no labels to score against. Derive them from the register or import a ground-truth file first.", status_code=409, code="NO_LABELS")
  
    sheets = await self.core.repo.sheets(org, drawing_id)
    label_sheets = sheets if label_drawing == drawing_id else await self.core.repo.sheets(org, label_drawing)
    page_of = {s.id: s.page_no for s in label_sheets}
    by_page: dict = {}
    labels = [_label_dict(r) for r in label_rows]
    for l in labels:
      by_page.setdefault(page_of.get(l["sheet_id"]), []).append(l)
    own_pages = {s.page_no for s in sheets}
    wanted = set(payload.sheet_ids) if payload.sheet_ids else None
    deadline = time.monotonic() + float(payload.max_total_seconds)
    scored, cannot, versions, partial = [], [], set(), wanted is not None
    
    for sheet in sheets:
      title = getattr(sheet, "label", None)
      head = {"sheet_id": str(sheet.id), "page_no": sheet.page_no, "title": title}
      mine = by_page.get(sheet.page_no)
      
      if wanted is not None and sheet.id not in wanted:
        cannot.append({**head, "reason": "NOT_SELECTED", "detail": NOT_JUDGED["NOT_SELECTED"]})
        continue
      if not mine:
        cannot.append({**head, "reason": "NO_LABELS", "detail": NOT_JUDGED["NO_LABELS"]})
        continue
      if mode == "DRY_RUN" and time.monotonic() > deadline:
        cannot.append({**head, "reason": "TIME_LIMIT", "detail": NOT_JUDGED["TIME_LIMIT"]})
        partial = True
        continue
      try:
        reads, version = await self._reads(org, sheet, mode, float(payload.budget_seconds))
      except Unreadable as e:
        cannot.append({**head, "reason": e.code, "detail": NOT_JUDGED.get(e.code, e.code) + (f" ({e.detail})" if e.detail else "")})
        continue
      versions.add(version)
      scored.append({**head, **S.score_sheet(mine, reads, rule), "read": True})
      
    for page in sorted(p for p in by_page if p is not None and p not in own_pages):
      cannot.append({"sheet_id": None, "page_no": page, "title": None, "reason": "NO_MATCHING_SHEET", "detail": NOT_JUDGED["NO_MATCHING_SHEET"]})
    if not scored:
      reasons = sorted({c["reason"] for c in cannot})
      raise TraceException("No sheet could be scored (" + ", ".join(reasons) + "). Read the sheets, set their scale, or check the sheet numbers of the labels.", status_code=409, code="NOTHING_SCORED")
    if any(c["reason"] in ("NOT_READ", "NOT_PREPARED", "NO_SCALE", "READ_FAILED") for c in cannot):
      partial = True
      
    pos = sum(1 for l in labels if l["polarity"] == L.POSITIVE)
    summary = {"labels": len(labels), "positive": pos, "negative": len(labels) - pos, "sheets_with_labels": len({p for p in by_page if p is not None}),
      "complete_sheets": sum(1 for s in scored if s["basis"] == "COMPLETE"), "sources": sorted({l["source"] for l in labels})}
    extract_version = max(versions) if versions else None
    result = S.assemble(scored, cannot, rule, mode=mode, extract_version=extract_version, analysis_version=ANALYSIS_VERSION if mode == "DRY_RUN" else None,
      partial=partial, label_summary=summary)
    stamp, rhash = L.stamp(labels), S.rule_hash(rule)
    prior = await self.store.comparable(org, drawing_id, rhash, stamp, mode, None if label_drawing == drawing_id else label_drawing)
    best = S.best_of([(str(p.id), p.result) for p in prior])
    baseline, status = None, "PARTIAL" if partial else "OK"
    
    if best is not None and not partial:
      reasons = S.regression_reasons(result, best["result"], rule)
      baseline = {"score_id": best["id"], "f1": best["result"]["totals"].get("f1"), "extract_version": best["result"].get("extract_version"), "reasons": reasons}
      status = "REGRESSION" if reasons else "OK"
    elif best is None and not partial:
      baseline = {"score_id": None, "reasons": [], "note": "First score for these labels and this rule: nothing to compare with yet."}
    row = ReadingScore(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, label_drawing_id=None if label_drawing == drawing_id else label_drawing,
      extract_version=extract_version, analysis_version=result["analysis_version"], mode=mode, status=status, rule_hash=rhash, labels_stamp=stamp, label_count=len(labels),
      overall_f1=None if result["totals"]["f1"] is None else Decimal(str(result["totals"]["f1"])), result=result, baseline=baseline, note=payload.note, created_by_user_id=user_id, created_at=datetime.now(timezone.utc))
    self.store.add_score(row)
    await self.session.flush()
    await self.session.commit()
    await self.session.refresh(row)
    return {**score_item(row), "result": row.result, "baseline": row.baseline}

  async def list_scores(self, org: UUID, drawing_id: UUID, limit: int = 50) -> dict:
    await self._drawing(org, drawing_id)
    rows = await self.store.scores(org, drawing_id, limit)
    best = S.best_of([(str(r.id), r.result) for r in rows if r.status != "PARTIAL"])
    return {"drawing_id": drawing_id, "current_extract_version": C.EXTRACT_VERSION, "best_id": UUID(best["id"]) if best else None, "scores": [score_item(r) for r in rows]}

  async def get_score(self, org: UUID, score_id: UUID) -> dict:
    row = await self.store.score(org, score_id)
    if row is None:
      raise TraceException("Score not found.", status_code=404, code="SCORE_NOT_FOUND")
    return {**score_item(row), "result": row.result, "baseline": row.baseline}

  async def compare(self, org: UUID, drawing_id: UUID, a: UUID, b: UUID) -> dict:
    await self._drawing(org, drawing_id)
    ra, rb = await self.store.score(org, a), await self.store.score(org, b)
    if ra is None or rb is None:
      raise TraceException("Score not found.", status_code=404, code="SCORE_NOT_FOUND")
    if ra.drawing_id != drawing_id or rb.drawing_id != drawing_id:
      raise TraceException("Both scores must be of this drawing.", status_code=409, code="SCORE_OTHER_DRAWING")
    return {"drawing_id": drawing_id, "a": score_item(ra), "b": score_item(rb), "comparison": S.compare(ra.result, rb.result)}
