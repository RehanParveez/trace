from __future__ import annotations
from datetime import datetime, timezone
import tempfile
from app.modules.drawings_boq.takeoff.prep.extract import PdfOpenError, extract_page, open_document
from app.modules.drawings_boq.takeoff.service import TakeoffService, build_calibration
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.prep_repository import PrepRepository
from app.modules.drawings_boq.models import TakeoffCalibration
from decimal import Decimal
import asyncio
from uuid import UUID, uuid4
import math
import os
import time
from app.engine.measure import takeoff as tk
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff import repository as repo_mod
from app.modules.drawings_boq.takeoff.prep import census
from app.modules.drawings_boq.takeoff.prep.analyze import ANALYSIS_VERSION, analyze_page
from app.modules.drawings_boq.takeoff.prep.codec import encode_index
from app.shared.storage import download_to_path

SNAP_VERIFY_TOL_PT = 0.12
TAG_VERIFY_RADIUS_PT = 14.0
STANDARD_WALLS_MM = (75, 100, 115, 125, 150, 200, 230, 250, 300, 343, 350, 450)
MAX_VECTOR_SEGMENTS = 60000

def _now() -> datetime:
  return datetime.now(timezone.utc)

def _fmt(v: float, places: int = 3) -> float:
  return round(float(v), places)

def compact_scale(full: dict) -> dict:
  declared = full.get("declared") or {}
  measured = full.get("measured") or {}
  return {
    "version": full.get("version"), "agreement": full.get("agreement"), "recommended": full.get("recommended"),
    "declared": declared.get("primary"), "multi_scale": bool(declared.get("multi_scale")), "not_to_scale": bool(declared.get("not_to_scale")),
    "clusters": measured.get("clusters") or [], "dimensions_read": measured.get("pairs_found", 0),
    "dimension_mismatches": len(measured.get("mismatches") or []), "notes": full.get("notes") or [],
    "paper": full.get("paper"), "units_hint": full.get("units_hint"),
  }

def _download_bytes(storage_key: str) -> bytes:
  with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "drawing.pdf")
    download_to_path(storage_key, path)
    with open(path, "rb") as handle:
      return handle.read()

def _open(contents: bytes):
  try:
    return open_document(contents)
  except PdfOpenError as exc:
    raise TraceException(exc.message, status_code=422, code=exc.code)

def _analyze_one(doc, page_no: int, user_unit: float, budget_s: float):
  raw = extract_page(doc, page_no - 1, budget_s=budget_s)
  result = analyze_page(raw, user_unit, budget_s=max(5.0, budget_s / 2))
  return result, raw.stats

class PrepService:
  def __init__(self, session):
    self.session = session
    self.core = TakeoffService(session)
    self.repo = self.core.repo
    self.prep = PrepRepository(session)

  async def _sheet(self, org: UUID, sheet_id: UUID, lock: bool = False):
    return await self.core._sheet(org, sheet_id, lock=lock)

  async def _index(self, org: UUID, sheet_id: UUID):
    index = await self.prep.load_index(org, sheet_id)
    if index is None:
      raise TraceException("Prepare this sheet first; its geometry has not been read yet.", status_code=409, code="SHEET_NOT_PREPARED")
    return index

  async def _mm_per_pt(self, org: UUID, sheet, calibration_id: UUID | None = None) -> Decimal | None:
    cal = None
    if calibration_id is not None:
      cal = await self.core._calibration(org, calibration_id)
      if cal.sheet_id != sheet.id:
        raise TraceException("That calibration belongs to another sheet.", status_code=422, code="CALIBRATION_WRONG_SHEET")
    else:
      cal = await self.core._default_calibration(org, sheet.id)
    if cal is None or not cal.usable:
      return None
    ev = tk.evaluate_calibration(repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet)))
    return ev.mm_per_pt if ev.usable else None

  @staticmethod
  def _stale(sheet) -> bool:
    return (sheet.prep_meta or {}).get("analysis_version") != ANALYSIS_VERSION

  async def prepare_drawing(self, org: UUID, drawing_id: UUID, user_id: UUID, payload) -> dict:
    started = time.monotonic()
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.repo.sheets(org, drawing_id)
    if not sheets:
      await self.core.sync_sheets(org, drawing_id, user_id)
      sheets = await self.repo.sheets(org, drawing_id)
    wanted = set(payload.sheet_ids) if payload.sheet_ids else None
    if wanted is not None:
      unknown = wanted - {s.id for s in sheets}
      if unknown:
        raise TraceException("Some sheets do not belong to this drawing.", status_code=422, code="SHEET_NOT_IN_DRAWING")
    candidates = [s for s in sheets if wanted is None or s.id in wanted]
    todo = [s for s in candidates if payload.force or s.prep_status != "READY" or self._stale(s)]
    skipped = [s.id for s in candidates if s not in todo]
    prepared: list = []
    failed: list = []
    if todo:
      contents = await asyncio.to_thread(_download_bytes, drawing.storage_key)
      doc = await asyncio.to_thread(_open, contents)
      try:
        for sheet in todo:
          if time.monotonic() - started > payload.budget_seconds and prepared:
            break
          try:
            ok = await self._prepare_one(org, user_id, drawing, sheet, doc, float(payload.budget_seconds))
          except TraceException as exc:
            ok = False
            await self._mark_failed(org, sheet.id, exc.message)
          if ok:
            prepared.append(sheet.id)
          else:
            failed.append({"sheet_id": str(sheet.id), "page_no": sheet.page_no})
      finally:
        try:
          doc.close()
        except Exception:
          pass
    refreshed = await self.repo.sheets(org, drawing_id)
    remaining = sum(1 for s in refreshed if (wanted is None or s.id in wanted) and (s.prep_status != "READY" or self._stale(s)) and s.prep_status != "FAILED")
    return {"drawing_id": drawing_id, "prepared": prepared, "skipped": skipped, "failed": failed, "remaining": remaining,
      "elapsed_seconds": round(time.monotonic() - started, 2), "sheets": refreshed}

  async def prepare_sheet(self, org: UUID, sheet_id: UUID, user_id: UUID, force: bool = False):
    sheet = await self._sheet(org, sheet_id)
    drawing = await self.core._pdf_drawing(org, sheet.drawing_id)
    if not force and sheet.prep_status == "READY" and not self._stale(sheet):
      return sheet
    contents = await asyncio.to_thread(_download_bytes, drawing.storage_key)
    doc = await asyncio.to_thread(_open, contents)
    try:
      ok = await self._prepare_one(org, user_id, drawing, sheet, doc, 60.0)
    finally:
      try:
        doc.close()
      except Exception:
        pass
    if not ok:
      raise TraceException(sheet.prep_error or "This sheet could not be read.", status_code=422, code="SHEET_PREP_FAILED")
    return await self._sheet(org, sheet_id)

  async def _mark_failed(self, org: UUID, sheet_id: UUID, message: str) -> None:
    sheet = await self._sheet(org, sheet_id, lock=True)
    sheet.prep_status, sheet.prep_error = "FAILED", (message or "")[:500]
    await self.session.flush()
    await self.session.commit()

  async def _prepare_one(self, org: UUID, user_id: UUID, drawing, sheet, doc, budget_s: float) -> bool:
    user_unit = float(repo_mod.sheet_user_unit(sheet))
    try:
      result, stats = await asyncio.to_thread(_analyze_one, doc, sheet.page_no, user_unit, min(budget_s, 40.0))
    except Exception as exc:  
      await self._mark_failed(org, sheet.id, f"Page {sheet.page_no} could not be read: {type(exc).__name__}")
      return False
  
    payload = await asyncio.to_thread(encode_index, result.index)
    full = result.detected_scale
    locked = await self._sheet(org, sheet.id, lock=True)
    old_meta = dict(locked.prep_meta or {})
    meta = {**result.meta, "prepared_at": _now().isoformat()}
    for keep in ("user_unit", "kind_source"):
      if keep in old_meta:
        meta[keep] = old_meta[keep]
    kind_changed = False
    if old_meta.get("kind_source") != "USER" and locked.content_kind != result.content_kind:
      locked.content_kind, kind_changed = result.content_kind, True
    locked.detected_scale = compact_scale(full)
    locked.prep_meta = meta
    
    locked.text_chars, locked.vector_ops = result.text_chars, result.vector_ops
    locked.prep_status, locked.prep_error = "READY", None
    primary = (full.get("declared") or {}).get("primary")
    if not locked.scale_text and primary:
      locked.scale_text = str(primary.get("text"))[:60]
    title = result.meta.get("title") or {}
    if not locked.label and (title.get("title") or title.get("sheet_no")):
      locked.label = " ".join(x for x in (title.get("sheet_no"), title.get("title")) if x)[:200]
    await self.prep.save(org, locked.id, ANALYSIS_VERSION, payload,
        {"segments": len(result.index.kinds), "rings": len(result.index.rings), "words": len(result.index.words)}, full)
    await self.session.flush()
    if kind_changed:
      await self.core._refresh_sheet_measurements(org, locked)
    await self.core._log(org, user_id, locked.id, AuditAction.UPDATE,
        f"Read sheet {locked.page_no} for takeoff ({result.content_kind.lower()}, scale check: {str(full.get('agreement')).lower().replace('_', ' ')})")
    await self.session.commit()
    return True

  async def analysis(self, org: UUID, sheet_id: UUID) -> dict:
    sheet = await self._sheet(org, sheet_id)
    row = await self.prep.meta(org, sheet_id)
    return {"sheet_id": sheet.id, "prep_status": sheet.prep_status, "stale": self._stale(sheet), "content_kind": sheet.content_kind,
      "detected_scale": (row.analysis if row is not None else None) or sheet.detected_scale or {}, "meta": sheet.prep_meta or {}}

  async def auto_calibrate(self, org: UUID, sheet_id: UUID, user_id: UUID, payload) -> dict:
    sheet = await self._sheet(org, sheet_id, lock=True)
    row = await self.prep.meta(org, sheet_id)
    if sheet.prep_status != "READY" or row is None or not row.analysis:
      raise TraceException("Prepare this sheet first; its scale has not been read yet.", status_code=409, code="SHEET_NOT_PREPARED")
    full = row.analysis
    
    rec = self._choose_recommendation(full, payload.use)
    if rec is None:
      raise TraceException("No scale or readable dimensions were found on this sheet. Calibrate with two points and a known distance.",
        status_code=422, code="NO_SCALE_RECOMMENDATION")
    user_unit = repo_mod.sheet_user_unit(sheet)
    created, cal = await self._ensure_calibration(org, sheet, user_id, rec, user_unit, make_default=payload.make_default)
    extra = []
    if payload.include_regions and full.get("agreement") == "MULTI_SCALE":
      for c in (full.get("measured") or {}).get("clusters", [])[1:3]:
        if c.get("support", 0) < 3 or not c.get("bbox"):
          continue
        sub = {"ratio": c["ratio"], "scale_text": f"1:{_trim(c['ratio'])}", "basis": "MEASURED_FROM_DIMENSIONS", "trust": 0.85,
          "check": None, "support": c["support"], "region": c["bbox"]}
        _, extra_cal = await self._ensure_calibration(org, sheet, user_id, sub, user_unit, make_default=False)
        extra.append(extra_cal)
    await self.session.commit()
    return {"calibration": cal, "additional": extra, "created": created, "recommendation": rec, "notes": full.get("notes") or []}

  @staticmethod
  def _choose_recommendation(full: dict, use: str) -> dict | None:
    rec = full.get("recommended")
    measured = full.get("measured") or {}
    clusters = measured.get("clusters") or []
    pairs = [p for p in (measured.get("pairs") or []) if p.get("inlier")]
    def best_check(pairs_):
      if not pairs_:
        return None
      p = max(pairs_, key=lambda t: t["quality"] * min(t["length_pt"], 400.0))
      return {"p1": p["p1"], "p2": p["p2"], "value": format(Decimal(str(p["value_mm"])).normalize(), "f"), "unit": "mm", "text": p["text"],
        "length_pt": p["length_pt"]}
    if use == "RECOMMENDED":
      return rec
    if use == "DECLARED":
      d = (full.get("declared") or {}).get("primary")
      
      if not d:
        return None
      return {"method": "SCALE_RATIO", "ratio": d["ratio"], "scale_text": d.get("text") or f"1:{_trim(d['ratio'])}", "basis": "DECLARED",
        "trust": d.get("trust", 0.6), "check": best_check(pairs), "support": len(pairs)}
    if use == "DIMENSIONS":
      if not clusters or clusters[0].get("support", 0) < 2:
        return None
      c = clusters[0]
      return {"method": "SCALE_RATIO", "ratio": c["ratio"], "scale_text": f"1:{_trim(c['ratio'])}", "basis": "MEASURED_FROM_DIMENSIONS",
        "trust": 0.85, "check": best_check(pairs), "support": c["support"]}
    return None

  async def _ensure_calibration(self, org: UUID, sheet, user_id: UUID, rec: dict, user_unit: Decimal, make_default: bool):
    check = None
    if rec.get("check"):
      ck = rec["check"]
      check = {"p1": ck["p1"], "p2": ck["p2"], "known_mm": Decimal(str(ck["value"]))}
    cols = build_calibration("SCALE_RATIO", None, Decimal(str(rec["ratio"])), rec.get("scale_text"), check, user_unit)
    auto = {"basis": rec.get("basis"), "trust": rec.get("trust"), "support": rec.get("support"), "version": ANALYSIS_VERSION}
    if rec.get("region"):
      auto["region"] = rec["region"]
    cols["ref"] = {**(cols.get("ref") or {}), "auto": auto}
    label = self._label(rec)
    
    existing = [c for c in await self.repo.calibrations(org, [sheet.id]) if (c.ref or {}).get("auto") and c.method == "SCALE_RATIO"
      and c.ratio is not None and abs(Decimal(c.ratio) / cols["ratio"] - 1) < Decimal("0.0001")
      and (c.check_ref or None) == (cols["check_ref"] or None) and ((c.ref or {}).get("auto") or {}).get("region") == auto.get("region")]
    if existing:
      cal = existing[0]
      if make_default and cal.usable and not cal.is_default:
        await self.core._set_default(org, sheet.id, cal)
      return False, cal
    cal = TakeoffCalibration(id=uuid4(), organization_id=org, sheet_id=sheet.id, label=label, created_by_user_id=user_id, is_default=False, **cols)
    self.session.add(cal)
    await self.session.flush()
    others = [c for c in await self.repo.calibrations(org, [sheet.id]) if c.id != cal.id and c.usable and c.is_default]
    if cal.usable and (make_default or not others):
      await self.core._set_default(org, sheet.id, cal)
    await self.core._log(org, user_id, cal.id, AuditAction.CREATE,
      f"Auto-calibrated sheet {sheet.page_no} from {str(rec.get('basis')).lower().replace('_', ' ')} ({'usable' if cal.usable else 'not usable'})")
    return True, cal

  @staticmethod
  def _label(rec: dict) -> str:
    base = f"Auto 1:{_trim(rec['ratio'])}"
    n = rec.get("support") or 0
    if rec.get("region"):
      return f"{base} (view)"[:120]
    if n:
      return f"{base} · {n} printed dimension{'s' if n != 1 else ''} agree"[:120]
    return f"{base} · printed scale, unverified"[:120]

  async def vector_window(self, org: UUID, sheet_id: UUID, bbox: tuple | None, max_segments: int) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    x0, y0, x1, y1 = bbox if bbox else index.bbox
    cap = max(100, min(int(max_segments), MAX_VECTOR_SEGMENTS))
    edges, total, truncated = index.window(x0, y0, x1, y1, cap)
    return {"bbox": [_fmt(x0), _fmt(y0), _fmt(x1), _fmt(y1)],
      "segments": [[_fmt(a), _fmt(b), _fmt(c), _fmt(d), int(k)] for a, b, c, d, k in edges], "total": total, "truncated": truncated}

  async def text(self, org: UUID, sheet_id: UUID, query: str | None, mode: str, bbox: tuple | None, limit: int = 5000) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    if query:
      words = census.find_words(index.words, query, "WORD" if mode == "WORD" else "CONTAINS" if mode == "CONTAINS" else "TAG")
      if bbox:
        words = [w for w in words if bbox[0] <= w["x"] <= bbox[2] and bbox[1] <= w["y"] <= bbox[3]]
    else:
      src = index.words
      if bbox:
        src = [w for w in src if bbox[0] <= w.cx <= bbox[2] and bbox[1] <= w.cy <= bbox[3]]
      words = [{"text": w.text, "x": _fmt(w.cx), "y": _fmt(w.cy), "angle": _fmt(w.angle, 1), "size": _fmt(w.size, 2)} for w in src]
    total = len(words)
    return {"total": total, "words": words[:limit], "truncated": total > limit}

  async def snap(self, org: UUID, sheet_id: UUID, payload) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    want = tuple(payload.want) if payload.want else ("ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE")
    out = []
    for x, y in payload.points:
      hit = index.nearest(float(x), float(y), payload.radius_pt, want)
      if hit is None:
        out.append({"input": [float(x), float(y)], "snapped": False})
      else:
        out.append({"input": [float(x), float(y)], "snapped": True, "x": _fmt(hit["x"], 4), "y": _fmt(hit["y"], 4), "kind": hit["kind"],
          "distance": _fmt(hit["distance"], 4)})
    return {"results": out}

  async def pick(self, org: UUID, sheet_id: UUID, payload) -> dict:
    sheet = await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    x, y = float(payload.point[0]), float(payload.point[1])
    mm_per_pt = await self._mm_per_pt(org, sheet, payload.calibration_id)
    hit = index.nearest(x, y, payload.radius_pt)
    snap = None if hit is None else {"x": _fmt(hit["x"], 4), "y": _fmt(hit["y"], 4), "kind": hit["kind"], "distance": _fmt(hit["distance"], 4)}
    wall = None
    if payload.wall and hit is not None:
      if mm_per_pt:
        w = index.wall_at(x, y, float(mm_per_pt), radius=payload.radius_pt)
      else:
        edge = index.nearest(x, y, payload.radius_pt, want=("EDGE",))
        w = {"run": list(index.run_of(edge["segment"])), "partner": None} if edge is not None and not index.kinds[edge["segment"]] else None
      if w is not None:
        wall = {"run": [[_fmt(v, 4) for v in p] for p in w["run"]], "partner": None}
        
        if w.get("partner"):
          part = w["partner"]
          t = part["thickness_mm"]
          near = min(STANDARD_WALLS_MM, key=lambda s_: abs(t / s_ - 1.0))
          wall.update({"partner": True, "centreline": [[_fmt(v, 4) for v in p] for p in w["centreline"]], "overlap": _fmt(part["overlap"], 3),
            "offset_pt": _fmt(part["offset_pt"], 4), "thickness_mm": _fmt(t, 1),
            "suggested_thickness_mm": near if abs(t / near - 1.0) <= 0.04 else int(round(t / 5.0) * 5)})
        elif not mm_per_pt:
          wall["note"] = "Calibrate the sheet to read the wall thickness."
          
    region = None
    if payload.region:
      found = index.region_at(x, y)
      if found is not None:
        ring_i, holes = found
        r = index.rings[ring_i]
        per = sum(math.dist(r.pts[i], r.pts[(i + 1) % len(r.pts)]) for i in range(len(r.pts)))
        region = {"outer": [[_fmt(a, 4), _fmt(b, 4)] for a, b in r.pts], "area_pt2": _fmt(r.area, 3), "perimeter_pt": _fmt(per, 3),
          "holes": [{"ring": [[_fmt(a, 4), _fmt(b, 4)] for a, b in index.rings[h].pts], "area_pt2": _fmt(index.rings[h].area, 3)} for h in holes[:30]]}
        if mm_per_pt:
          f = float(mm_per_pt)
          region["area_m2"] = _fmt(r.area * f * f / 1e6, 4)
          region["perimeter_m"] = _fmt(per * f / 1000.0, 3)
          region["holes_area_m2"] = _fmt(sum(index.rings[h].area for h in holes) * f * f / 1e6, 4)
          
    labels = []
    if payload.label_radius_pt > 0:
      for w in index.words:
        d = math.hypot(w.cx - x, w.cy - y)
        if d <= payload.label_radius_pt:
          labels.append((d, {"text": w.text, "x": _fmt(w.cx), "y": _fmt(w.cy), "distance": _fmt(d, 2)}))
      labels.sort(key=lambda t: t[0])
    return {"snap": snap, "wall": wall, "region": region, "labels": [l for _, l in labels[:20]],
        "mm_per_pt": format(mm_per_pt.normalize(), "f") if mm_per_pt else None}

  async def tags(self, org: UUID, sheet_id: UUID) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    return {"tags": [{"tag": g["tag"], "count": g["count"], "in_drawing": g["in_drawing"]} for g in census.tag_census(index.words)]}

  async def tag_detail(self, org: UUID, sheet_id: UUID, tag: str, include_dense: bool) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    hits = census.find_words(index.words, tag, "TAG")
    
    if not hits:
      raise TraceException(f"The tag {tag} was not found on this sheet.", status_code=404, code="TAG_NOT_FOUND")
    counted = [h for h in hits if include_dense or not h["dense"]]
    note = None
    dense = len(hits) - len([h for h in hits if not h["dense"]])
    if dense and not include_dense:
      note = f"{dense} occurrence(s) sit inside a dense block of text (a schedule, legend or notes) and are left out of the count."
    pts = [[h["x"], h["y"]] for h in counted]
    return {"tag": tag.strip().upper(), "count": len(hits), "in_drawing": len(hits) - dense,
      "points": [{"x": h["x"], "y": h["y"], "dense": h["dense"]} for h in hits],
      "suggestion": {"kind": "COUNT", "quantity_mode": "DIRECT", "geometry": {"points": pts}, "source": "TAG_SCAN",
        "tag": tag.strip().upper(), "label": f"{tag.strip().upper()} x{len(pts)}"},
      "note": note}

  async def shapes(self, org: UUID, sheet_id: UUID) -> dict:
    sheet = await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    mm = await self._mm_per_pt(org, sheet)
    groups = census.shape_groups(index.rings, max((index.bbox[2] - index.bbox[0]) * (index.bbox[3] - index.bbox[1]), 1.0))
    out = []
    for g in groups:
      out.append(self._shape_summary(g, mm))
    return {"shapes": out, "mm_per_pt": format(mm.normalize(), "f") if mm else None}

  @staticmethod
  def _shape_summary(g: dict, mm) -> dict:
    return {"id": g["id"], "shape": g["shape"], "a_pt": g["a_pt"], "b_pt": g["b_pt"],
      "a_mm": _fmt(g["a_pt"] * float(mm), 1) if mm else None, "b_mm": _fmt(g["b_pt"] * float(mm), 1) if mm else None,
        "count": g["count"], "filled": g["filled"]}

  async def shape_detail(self, org: UUID, sheet_id: UUID, group_id: str) -> dict:
    sheet = await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    mm = await self._mm_per_pt(org, sheet)
    for g in census.shape_groups(index.rings, max((index.bbox[2] - index.bbox[0]) * (index.bbox[3] - index.bbox[1]), 1.0)):
      if g["id"] == group_id:
        label = f"{g['shape'].title()} {g['count']} nos"
        return {"shape": self._shape_summary(g, mm), "points": g["points"],
          "suggestion": {"kind": "COUNT", "quantity_mode": "DIRECT", "geometry": {"points": g["points"]}, "source": "VECTOR_SNAP",
            "tag": None, "label": label}}
    raise TraceException("That shape group was not found on this sheet.", status_code=404, code="SHAPE_GROUP_NOT_FOUND")

  async def verified_source(self, org: UUID, sheet, kind: str, geometry: dict, source: str, tag: str | None = None) -> str:
    
    if source == "MANUAL":
      return "MANUAL"
    index = await self.prep.load_index(org, sheet.id)
    if index is None:
      return "MANUAL"
    pts: list = []
    if kind == "LENGTH":
      pts = list(geometry.get("points") or [])
    elif kind == "AREA":
      pts = list(geometry.get("outer") or []) + [p for h in (geometry.get("holes") or []) for p in h]
    else:
      pts = list(geometry.get("points") or [])
      
    if not pts:
      return "MANUAL"
    if kind == "COUNT":
      if source == "TAG_SCAN":
        if not tag:
          return "MANUAL"
        want = tag.strip().upper()
        words = [w for w in index.words if w.text.strip().upper() == want]
        ok = all(any(math.hypot(w.cx - p[0], w.cy - p[1]) <= TAG_VERIFY_RADIUS_PT for w in words) for p in pts)
        return "TAG_SCAN" if ok else "MANUAL"
      centres = [((r.bbox[0] + r.bbox[2]) / 2.0, (r.bbox[1] + r.bbox[3]) / 2.0) for r in index.rings]
      ok = all(any(math.hypot(c[0] - p[0], c[1] - p[1]) <= 1.0 for c in centres) or index.on_geometry(float(p[0]), float(p[1]), 3.0) for p in pts)
      return "VECTOR_SNAP" if ok else "MANUAL"
    if source != "VECTOR_SNAP":
      return "MANUAL"
    ok = all(index.on_geometry(float(p[0]), float(p[1]), SNAP_VERIFY_TOL_PT) for p in pts)
    return "VECTOR_SNAP" if ok else "MANUAL"

def _trim(v) -> str:
  s = format(Decimal(str(round(float(v), 4))).normalize(), "f")
  return s