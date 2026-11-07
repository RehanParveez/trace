from __future__ import annotations
import argparse
import asyncio
import copy
import json
import os
import sys
import uuid
from decimal import Decimal
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff.prep_service import PrepService
from app.modules.drawings_boq.takeoff.extract import drawing_passes_service as DPS
from app.modules.identity.models import Organization
from app.modules.projects.models import Project
from app.modules.drawings_boq.takeoff.proof import offline_accept as OA
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from sqlalchemy import text
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.engine.measure import rulebook as RB
from app.engine.measure import rule_registry as RR
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.database import Base
from app.modules.drawings_boq.models import Drawing, DrawingFormat, TakeoffExtraction
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import member_passes as MP
from app.modules.drawings_boq.takeoff.run import reader as RDR

URL_ENV = "TRACE_PARITY_DATABASE_URL"
SAFE_NAMES = ("check", "parity", "test")
COMPARED = ("label", "tag", "geometry", "params", "missing", "status", "facts", "notes")

def scratch_url() -> str:
  url = os.environ.get(URL_ENV) or ""
  name = url.rsplit("/", 1)[-1].split("?")[0].lower()
  if not url or not any(s in name for s in SAFE_NAMES):
    raise SystemExit(f"Set {URL_ENV} to a scratch database whose name contains one of {', '.join(SAFE_NAMES)}. The run drops and rebuilds every table in it.")
  return url

def plain(value):
  return json.loads(json.dumps(value, default=str))

def expected_state(reads: list) -> dict:
  out: dict = {}
  for _name, rows in reads:
    heights = PrepService.floor_heights_from([SimpleNamespace(page_no=r["page_no"], label=None, prep_meta=r.get("meta") or {}) for r in rows])["heights"]
    result = DPS.run_passes(rows, heights)
    for r in rows:
      for c in r["candidates"]:
        c.notes = DPS.deduplicated(c.notes)
        if (_name, r["page_no"], c.key) in out:
          continue
        out[(_name, r["page_no"], c.key)] = {"fields": plain({k: (c.label[:200] if k == "label" else getattr(c, k)) for k in COMPARED}), "decision": "REJECTED" if FS.is_set_aside(c) else "NEW"}
    out[(_name, "result")] = plain(result)
  return out

async def load(session: AsyncSession, case: str, reads: list, inputs: dict | None = None) -> dict:
  session.add(Organization(id=OA.ORG, name="parity", slug="parity"))
  session.add(Project(id=OA.PROJECT, organization_id=OA.ORG, name="parity"))
  await session.flush()
  
  ids: dict = {}
  for name, rows in reads:
    drawing_id = OA.uid(case, "drawing", name)
    session.add(Drawing(id=drawing_id, organization_id=OA.ORG, project_id=OA.PROJECT, original_filename=name, storage_key=f"parity/{name}", format=DrawingFormat.PDF, revision_group_id=uuid.uuid4(), ingestion_meta={MP.META_KEY: plain(inputs or {})}))
    await session.flush()
    ids[name] = drawing_id
    
    for r in rows:
      sheet = OA._sheet_for(case, drawing_id, r, {})
      session.add(sheet)
      await session.flush()
      mm = float(r.get("mm_per_pt") or 0.0)
      session.add(TakeoffExtraction(sheet_id=sheet.id, organization_id=OA.ORG, extract_version=C.EXTRACT_VERSION, mm_per_pt=Decimal(str(mm)) if mm else None, stats=plain(r.get("stats") or {}), unmapped_tags=[], notes=[]))
      seen: set = set()
      for c in r["candidates"]:
        if c.key in seen:
          continue
        seen.add(c.key)
        session.add(OA._candidate(c, sheet, mm, {}))
      await session.flush()
  return ids

async def state_of(svc: ExtractService, ids: dict, reads: list) -> dict:
  out: dict = {}
  
  for name, drawing_id in ids.items():
    sheets = await svc.core.repo.sheets(OA.ORG, drawing_id)
    page_of = {s.id: s.page_no for s in sheets}
    for row in await svc.repo.candidates(OA.ORG, [s.id for s in sheets]):
      out[(name, page_of[row.sheet_id], row.ckey)] = {"fields": plain({k: getattr(row, k) for k in COMPARED}), "decision": row.decision}
    drawing = await svc.core.repo.drawing(OA.ORG, drawing_id)
    out[(name, "result")] = plain((drawing.ingestion_meta or {}).get(DPS.META_KEY))
  return out

def comparable(entry):
  if not isinstance(entry, dict) or "fields" not in entry or entry.get("decision") != "REJECTED":
    return entry
  facts = {k: v for k, v in (entry["fields"].get("facts") or {}).items() if k != "footing_section_join"}
  return {**entry, "fields": {**entry["fields"], "facts": facts}}

def differences(want: dict, got: dict) -> list:
  out = []
  for key in sorted(set(want) | set(got), key=str):
    if key not in got:
      out.append((key, "missing in the database"))
    elif key not in want:
      out.append((key, "only in the database"))
    elif comparable(want[key]) != comparable(got[key]):
      if key[1] == "result":
        left, right = want[key] or {}, got[key] or {}
        bad = [k for k in sorted(set(left) | set(right)) if left.get(k) != right.get(k)]
        out.append((key, "pass results differ: " + ", ".join(bad)))
      else:
        bad = [k for k in COMPARED if comparable(want[key])["fields"].get(k) != comparable(got[key])["fields"].get(k)]
        if want[key]["decision"] != got[key]["decision"]:
          bad.append("decision")
        out.append((key, "differs in " + ", ".join(bad)))
        
  return out

async def run(case: str, files_dir: str) -> dict:
  spec = CIO.load_case(os.path.join(CIO.HERE, case))
  with RR.using(spec.get("overrides")):
    return await _run(case, files_dir)

async def _run(case: str, files_dir: str) -> dict:
  folder = os.path.join(CIO.HERE, case)
  spec = CIO.load_case(folder)
  files, _problems = CIO.find_files(spec, files_dir)
  rows, _bad, _file = CIO.load_company_rules(spec)
  inputs = {"sections": spec.get("sections"), "storeys": spec.get("storeys"), "runs": RR.on("BEAM_RUNS")}
  items = [(n, open(files[n], "rb").read()) for n in spec["pdfs"]]
  with RB.using_case(rows):
    full = [(n, r) for n, r, _p in RDR.read_set(items, **inputs)]
    reads = [(n, r) for n, r, _p in RDR.read_set(items, runs=inputs["runs"], structure=False)]
    
  want = expected_state([(n, copy.deepcopy(r)) for n, r in full])
  engine = create_async_engine(scratch_url(), poolclass=NullPool)
  async with engine.begin() as conn:
    await conn.execute(text("DROP SCHEMA public CASCADE"))
    await conn.execute(text("CREATE SCHEMA public"))
    await conn.run_sync(Base.metadata.create_all)
  maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
  
  async with maker() as session:
    ids = await load(session, case, reads, inputs)
    svc = ExtractService(session)
    unpassed = differences(want, await state_of(svc, ids, reads))
    touched_first = set()
    
    for drawing_id in ids.values():
      touched_first |= await DPS.reconcile_drawing_passes(svc, OA.ORG, drawing_id)
    await session.commit()
    first = await state_of(svc, ids, reads)
    touched_again = set()
    for drawing_id in ids.values():
      touched_again |= await DPS.reconcile_drawing_passes(svc, OA.ORG, drawing_id)
    await session.commit()
    again = await state_of(svc, ids, reads)
    
  await engine.dispose()
  diffs = differences(want, first)
  idem = differences(first, again)
  return {"case": case, "before_passes": len(unpassed), "candidates": sum(1 for k in want if len(k) == 3), "sheets_changed": len(touched_first), "differences": diffs, "second_run_changes": idem,
    "result": {k[0]: {a: (b if not isinstance(b, (list, dict)) else len(b)) for a, b in (want[k] or {}).items()} for k in want if len(k) == 2}}

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Put a case into PostgreSQL the way the application stores a read drawing, run the drawing passes of the application on it, and compare with the offline passes.")
  ap.add_argument("cases", nargs="+")
  ap.add_argument("--cases-dir")
  args = ap.parse_args(argv)
  files_dir = CIO.cases_dir(args.cases_dir)
  
  bad = 0
  for case in args.cases:
    got = asyncio.run(run(case, files_dir))
    print(f"{case}: {got['candidates']} candidates, {got['before_passes']} row(s) differ from the offline passes before the application passes run, {got['sheets_changed']} sheet(s) changed by the passes, {len(got['differences'])} difference(s) from the offline passes, {len(got['second_run_changes'])} change(s) on a second run")
    for key, why in got["differences"][:10] + got["second_run_changes"][:10]:
      print(f"  {key}: {why}")
    print(f"  pass results: {json.dumps(got['result'], default=str)[:300]}")
    bad += len(got["differences"]) + len(got["second_run_changes"])
  print("app parity passed" if not bad else f"app parity FAILED: {bad}")
  return 1 if bad else 0

if __name__ == "__main__":
  sys.exit(main())
